"""Automated compliance status for every ISO 42001 clause, Annex A control
and EU AI Act article.

Computed the same way lifecycle_gate_service computes stage-gate
requirements: read live from the records already in the system, never a
manual checkbox someone ticks. A control's status can't outlive the record
it depends on, and it re-opens by itself the moment that record is deleted,
retired, or falls out of review.

Four states, not two -- "tagged" and "actually covered" are different
questions:

- ``NOT_APPLICABLE`` -- the organization's Statement of Applicability says
  this Annex A control doesn't apply, with its recorded justification as the
  reason. Checked first: an excluded control is never "no coverage".
- ``NO_COVERAGE`` -- nothing is tagged to it at all, or every tag that once
  pointed at something now points at a deleted record.
- ``PARTIAL`` -- tagged, but at least one tagged item doesn't currently
  count: a draft or in-review Policy/Procedure, an assessment that hasn't
  reached its final approval, a retired document, or an approved/completed
  record whose review date has passed.
- ``SATISFIED`` -- every tagged item currently counts.

What this deliberately does not do: judge whether a policy's *content*
actually satisfies a clause. That's a compliance judgment a person makes when
tagging the record in the first place. This only tracks whether the thing
they pointed at is still there and still current.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.core import review_cadence
from app.models.ai_incident import AIIncident
from app.models.ai_objective import AIObjective
from app.models.audit_program import AuditProgram
from app.models.competence_requirement import CompetenceRequirement
from app.models.corrective_action import CorrectiveAction, CorrectiveActionStatus
from app.models.eu_ai_act_applicability import EuAiActApplicability
from app.models.evidence import Evidence
from app.models.framework_control import Framework, FrameworkControl
from app.models.framework_soa_entry import FrameworkSoaEntry, SoaApplicability
from app.models.impact_assessment import ImpactAssessment, ImpactAssessmentStatus
from app.models.policy import Policy, PolicyStatus
from app.models.procedure import Procedure, ProcedureStatus
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.supplier import Supplier
from app.repositories import (
    framework_control_repository,
    framework_soa_repository,
    framework_tag_repository,
    internal_audit_repository,
    management_review_repository,
    supplier_repository,
)
from app.schemas.compliance_status import (
    ComplianceStatusCounts,
    ComplianceStatusSummary,
    ControlComplianceStatus,
    TaggedItemStatus,
)
from app.services import (
    ai_incident_service,
    competence_service,
    corrective_action_service,
    eu_ai_act_service,
    internal_audit_service,
    management_review_service,
    objective_service,
    supplier_service,
)


class ComplianceStatus(StrEnum):
    SATISFIED = "satisfied"
    PARTIAL = "partial"
    NO_COVERAGE = "no_coverage"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class _Resolved:
    label: str
    current: bool
    detail: str


def _approval_like_state(
    *,
    status: str,
    approved_status: str,
    next_review_date: date | None,
    today: date,
    noun: str,
    draft_like: dict[str, str],
) -> tuple[bool, str]:
    """Shared shape for Policy/Procedure/assessment status: current only once
    approved/completed *and* still within its review cadence."""
    if status != approved_status:
        return False, draft_like.get(status, f"{noun} is {status.replace('_', ' ')}")
    if review_cadence.is_review_overdue(next_review_date, today):
        return False, f"{noun} approved, but its review date ({next_review_date}) has passed"
    return True, f"{noun} approved and current"


def _resolve_policy(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(Policy, entity_id)
    if record is None:
        return None
    current, detail = _approval_like_state(
        status=record.status,
        approved_status=PolicyStatus.APPROVED,
        next_review_date=record.next_review_date,
        today=today,
        noun="Policy",
        draft_like={
            PolicyStatus.DRAFT: "Policy is still in draft",
            PolicyStatus.IN_REVIEW: "Policy is awaiting approval",
            PolicyStatus.RETIRED: "Policy has been retired",
        },
    )
    return _Resolved(record.title, current, detail)


def _resolve_procedure(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(Procedure, entity_id)
    if record is None:
        return None
    current, detail = _approval_like_state(
        status=record.status,
        approved_status=ProcedureStatus.APPROVED,
        next_review_date=record.next_review_date,
        today=today,
        noun="Procedure",
        draft_like={
            ProcedureStatus.DRAFT: "Procedure is still in draft",
            ProcedureStatus.IN_REVIEW: "Procedure is awaiting approval",
            ProcedureStatus.RETIRED: "Procedure has been retired",
        },
    )
    return _Resolved(record.title, current, detail)


def _resolve_impact_assessment(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(ImpactAssessment, entity_id)
    if record is None:
        return None
    current, detail = _approval_like_state(
        status=record.status,
        approved_status=ImpactAssessmentStatus.COMPLETED,
        next_review_date=record.next_review_date,
        today=today,
        noun="Impact assessment",
        draft_like={
            ImpactAssessmentStatus.DRAFT: "Impact assessment is still in draft",
            ImpactAssessmentStatus.PENDING_OWNER_APPROVAL: (
                "Impact assessment is awaiting owner approval"
            ),
            ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL: (
                "Impact assessment is awaiting CAIGO approval"
            ),
        },
    )
    return _Resolved(f"Impact Assessment #{record.id}", current, detail)


def _resolve_risk_assessment(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(RiskAssessment, entity_id)
    if record is None:
        return None
    current, detail = _approval_like_state(
        status=record.status,
        approved_status=RiskAssessmentStatus.COMPLETED,
        next_review_date=record.next_review_date,
        today=today,
        noun="Risk assessment",
        draft_like={
            RiskAssessmentStatus.DRAFT: "Risk assessment is still in draft",
            RiskAssessmentStatus.IN_PROGRESS: "Risk assessment is in progress",
            RiskAssessmentStatus.PENDING_OWNER_APPROVAL: (
                "Risk assessment is awaiting owner approval"
            ),
            RiskAssessmentStatus.PENDING_CAIGO_APPROVAL: (
                "Risk assessment is awaiting CAIGO approval"
            ),
        },
    )
    return _Resolved(f"Risk Assessment #{record.id}", current, detail)


def _resolve_evidence(db: Session, entity_id: int, _today: date) -> _Resolved | None:
    record = db.get(Evidence, entity_id)
    if record is None:
        return None
    # A document has no approval stage of its own to be current or stale
    # against -- its presence is the signal, the same rule
    # lifecycle_gate_service uses for a required upload.
    return _Resolved(record.filename, True, "Document attached")


def _resolve_corrective_action(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(CorrectiveAction, entity_id)
    if record is None:
        return None
    if record.status == CorrectiveActionStatus.CLOSED:
        return _Resolved(record.title, True, "Corrective action verified and closed")
    if corrective_action_service.is_overdue(record.due_date, record.status, today):
        return _Resolved(record.title, False, f"Corrective action overdue since {record.due_date}")
    return _Resolved(record.title, True, f"Corrective action in progress, due {record.due_date}")


def _resolve_audit_program(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(AuditProgram, entity_id)
    if record is None:
        return None
    audits = internal_audit_repository.list_for_program(db, entity_id)
    if internal_audit_service.is_overdue(record, audits, today):
        due = internal_audit_service.next_due_date(record, audits)
        return _Resolved(record.title, False, f"Internal audit overdue since {due}")
    return _Resolved(record.title, True, "Internal audit program current")


def _resolve_management_review_settings(
    db: Session, entity_id: int, today: date
) -> _Resolved | None:
    # Unlike every other resolver, this singleton "exists" (with its
    # not-yet-configured defaults) whether or not a row has ever been
    # saved -- the same reasoning risk_criteria_service.get_criteria
    # follows for RiskCriteria's own singleton.
    if entity_id != management_review_service.SETTINGS_ENTITY_ID:
        return None
    record = management_review_service.get_settings(db)
    meetings = management_review_repository.list_meetings(db)
    if management_review_service.is_overdue(record, meetings, today):
        due = management_review_service.next_due_date(record, meetings)
        return _Resolved("Management review", False, f"Management review overdue since {due}")
    return _Resolved("Management review", True, "Management review current")


def _resolve_ai_incident(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(AIIncident, entity_id)
    if record is None:
        return None
    if ai_incident_service.is_reporting_overdue(record, today):
        deadline = ai_incident_service.reporting_deadline(record)
        return _Resolved(
            record.title, False, f"Serious incident not reported to the authority by {deadline}"
        )
    return _Resolved(record.title, True, f"Incident {record.status}")


def _resolve_competence_requirement(
    db: Session, entity_id: int, today: date
) -> _Resolved | None:
    record = db.get(CompetenceRequirement, entity_id)
    if record is None:
        return None
    people = competence_service.people_for(db, record, today)
    gaps = competence_service.gap_count(people)
    if gaps:
        return _Resolved(record.title, False, f"{gaps} of {len(people)} people not yet competent")
    return _Resolved(record.title, True, f"{len(people)} of {len(people)} people competent")


def _resolve_supplier(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(Supplier, entity_id)
    if record is None:
        return None
    review_dates = [
        review.review_date
        for review in supplier_repository.list_reviews_for_supplier(db, entity_id)
    ]
    standing = supplier_service.standing(record, review_dates, today)
    if standing.review_overdue:
        return _Resolved(
            record.name, False, f"Supplier review overdue since {standing.next_review_due}"
        )
    if standing.contract_status == "expired":
        return _Resolved(record.name, False, f"Supplier contract ended {record.contract_end}")
    return _Resolved(record.name, True, f"Supplier {record.status}")


def _format_value(value: float, unit: str | None) -> str:
    number = f"{value:g}"
    if not unit:
        return number
    # "82%" but "12 days" -- matching the frontend's formatValue.
    return f"{number}{unit}" if unit == "%" else f"{number} {unit}"


def _resolve_ai_objective(db: Session, entity_id: int, today: date) -> _Resolved | None:
    record = db.get(AIObjective, entity_id)
    if record is None:
        return None
    standing = objective_service.standing(
        record, objective_service.list_measurements(db, entity_id), today
    )
    if standing.measurement_overdue:
        return _Resolved(
            record.title, False, f"Measurement overdue since {standing.next_measurement_due}"
        )
    if standing.state in ("off_track", "missed") and standing.latest_value is not None:
        comparison = "≥" if record.direction == "at_least" else "≤"
        target = _format_value(record.target_value or 0, record.unit)
        latest = _format_value(standing.latest_value, record.unit)
        verb = "Target missed" if standing.state == "missed" else "Off target"
        return _Resolved(record.title, False, f"{verb}: {latest} vs {comparison} {target}")
    if standing.state == "missed":
        return _Resolved(record.title, False, f"Target date {record.target_date} passed unmet")
    labels = {
        # Before its first reading is due -- once it's due and missing, the
        # overdue check above has already caught it.
        "not_measured": "Awaiting its first reading",
        "on_track": "Objective on track",
        "in_progress": "Milestone in progress",
        "achieved": "Objective achieved",
        "not_achieved": "Objective closed as not achieved",
        "withdrawn": "Objective withdrawn",
    }
    return _Resolved(record.title, True, labels[standing.state])


_RESOLVERS = {
    "Policy": _resolve_policy,
    "Procedure": _resolve_procedure,
    "ImpactAssessment": _resolve_impact_assessment,
    "RiskAssessment": _resolve_risk_assessment,
    "AuditProgram": _resolve_audit_program,
    "Evidence": _resolve_evidence,
    "CorrectiveAction": _resolve_corrective_action,
    "ManagementReviewSettings": _resolve_management_review_settings,
    "AIIncident": _resolve_ai_incident,
    "CompetenceRequirement": _resolve_competence_requirement,
    "Supplier": _resolve_supplier,
    "AIObjective": _resolve_ai_objective,
}


def _resolve_tagged_item(
    db: Session, entity_type: str, entity_id: int, today: date
) -> _Resolved | None:
    resolver = _RESOLVERS.get(entity_type)
    if resolver is None:
        # An entity type with no rule of its own still gets a generic label
        # rather than being dropped -- unknown is not the same as gone, the
        # same principle framework_service._resolve_label already applies.
        return _Resolved(f"{entity_type} #{entity_id}", True, "Tagged, no freshness rule defined")
    return resolver(db, entity_id, today)


def _control_status(
    *, excluded_reason: str | None, items: list[TaggedItemStatus]
) -> tuple[str, str]:
    if excluded_reason is not None:
        return ComplianceStatus.NOT_APPLICABLE, excluded_reason
    if not items:
        return ComplianceStatus.NO_COVERAGE, "Nothing in the system is tagged to this control yet."
    if all(item.current for item in items):
        return ComplianceStatus.SATISFIED, f"Covered by {len(items)} current record(s)."
    stale = [item for item in items if not item.current]
    return (
        ComplianceStatus.PARTIAL,
        f"{len(stale)} of {len(items)} tagged record(s) need attention: {stale[0].detail}.",
    )


def _excluded_reason(
    control: FrameworkControl,
    soa_entry: FrameworkSoaEntry | None,
    eu_ai_act_settings: EuAiActApplicability | None,
) -> str | None:
    """Why a control doesn't apply, or None if it does. Annex A controls
    follow the Statement of Applicability; EU AI Act articles follow the
    organization's applicability assessment, or a per-article override."""
    if control.framework == Framework.EU_AI_ACT:
        applicable, reason = eu_ai_act_service.effective_applicability(
            eu_ai_act_settings, control.code, soa_entry
        )
        return None if applicable else reason
    if control.category == "annex_a_control" and soa_entry is not None:
        if soa_entry.applicability == SoaApplicability.NOT_APPLICABLE:
            return (
                soa_entry.justification
                or "Marked not applicable in the Statement of Applicability."
            )
    return None


def get_status(db: Session, framework: str | None = None) -> list[ControlComplianceStatus]:
    """Every control's computed status, in the same reading order the
    mapping and SoA views already use."""
    today = datetime.now(UTC).date()
    controls = framework_control_repository.list_all(db, framework)
    tags_by_control = framework_tag_repository.list_all_grouped_by_control(db)
    soa_by_control = {
        entry.framework_control_id: entry for entry in framework_soa_repository.list_all(db)
    }
    eu_ai_act_settings = eu_ai_act_service.get_settings(db)

    results = []
    for control in controls:
        excluded_reason = _excluded_reason(
            control, soa_by_control.get(control.id), eu_ai_act_settings
        )

        items: list[TaggedItemStatus] = []
        for tag in tags_by_control.get(control.id, []):
            resolved = _resolve_tagged_item(db, tag.entity_type, tag.entity_id, today)
            if resolved is None:
                continue  # The tagged record itself is gone -- not coverage.
            items.append(
                TaggedItemStatus(
                    entity_type=tag.entity_type,
                    entity_id=tag.entity_id,
                    label=resolved.label,
                    current=resolved.current,
                    detail=resolved.detail,
                )
            )

        status, reason = _control_status(excluded_reason=excluded_reason, items=items)

        results.append(
            ControlComplianceStatus(
                id=control.id,
                framework=control.framework,
                code=control.code,
                title=control.title,
                description=control.description,
                category=control.category,
                status=status,
                reason=reason,
                tagged_items=items,
            )
        )
    return results


def get_summary(db: Session) -> ComplianceStatusSummary:
    """Status counts, split the way the Compliance page groups controls --
    ISO's main-body clauses, its Annex A controls, and the EU AI Act
    articles are different obligations and don't average meaningfully
    together."""
    statuses = get_status(db)

    def _counts(rows: list[ControlComplianceStatus]) -> ComplianceStatusCounts:
        tally = {s: 0 for s in ComplianceStatus}
        for row in rows:
            tally[row.status] += 1
        return ComplianceStatusCounts(
            satisfied=tally[ComplianceStatus.SATISFIED],
            partial=tally[ComplianceStatus.PARTIAL],
            no_coverage=tally[ComplianceStatus.NO_COVERAGE],
            not_applicable=tally[ComplianceStatus.NOT_APPLICABLE],
        )

    return ComplianceStatusSummary(
        iso_42001_clauses=_counts(
            [s for s in statuses if s.framework == "iso_42001" and s.category == "clause"]
        ),
        iso_42001_annex_a=_counts(
            [s for s in statuses if s.framework == "iso_42001" and s.category == "annex_a_control"]
        ),
        eu_ai_act=_counts([s for s in statuses if s.framework == "eu_ai_act"]),
        eu_ai_act_scope=eu_ai_act_service.scope_of(eu_ai_act_service.get_settings(db)),
    )
