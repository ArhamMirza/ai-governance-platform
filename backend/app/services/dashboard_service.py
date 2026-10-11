from collections import Counter
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import review_cadence, risk_scoring
from app.models.ai_incident import AIIncidentStatus
from app.models.competence_requirement import CompetenceRequirement
from app.models.corrective_action import CorrectiveAction, CorrectiveActionStatus
from app.models.impact_assessment import ImpactAssessmentStatus
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import SheetRow
from app.repositories import (
    ai_incident_repository,
    ai_system_lifecycle_repository,
    corrective_action_repository,
    impact_assessment_repository,
    internal_audit_repository,
    management_review_repository,
    policy_repository,
    procedure_repository,
    risk_assessment_repository,
    sheet_repository,
    supplier_repository,
    user_repository,
)
from app.schemas.competence import PersonCompetence
from app.schemas.dashboard import (
    AISystemSummary,
    AttentionItem,
    CoverageSummary,
    DashboardSummary,
    MyCorrectiveActionItem,
    MyRiskItem,
    MyTrainingItem,
    RiskAssessmentSummary,
    StatusCounts,
)
from app.services import (
    ai_incident_service,
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    change_service,
    communication_service,
    competence_service,
    compliance_status_service,
    concern_service,
    corrective_action_service,
    data_inventory_service,
    governance_role_service,
    internal_audit_service,
    management_review_service,
    objective_service,
    pending_approvals_service,
    risk_analytics_service,
    risk_criteria_service,
    supplier_service,
)

APPROVED_STATUS = "approved"
IN_REVIEW_STATUS = "in_review"
RETIRED_STATUS = "retired"
HIGH_RISK_TIER = "high"

# The areas the attention panel is split into -- what someone would go and
# fix, rather than which table the count came from.
INCIDENTS_GROUP = "Incidents & corrective actions"
RISK_GROUP = "Risk & assessments"
OBJECTIVES_GROUP = "Objectives & performance"
PLANNING_GROUP = "Management system planning"
AUDIT_GROUP = "Audits & management review"
INVENTORY_GROUP = "AI systems, data & suppliers"
COMPLIANCE_GROUP = "Framework coverage"
PEOPLE_GROUP = "People & documents"
ATTENTION_GROUP_ORDER = [
    INCIDENTS_GROUP,
    RISK_GROUP,
    OBJECTIVES_GROUP,
    AUDIT_GROUP,
    PLANNING_GROUP,
    INVENTORY_GROUP,
    COMPLIANCE_GROUP,
    PEOPLE_GROUP,
]


def _attention(
    *,
    overdue_count: int,
    unassessed_count: int,
    no_impact_assessment_count: int,
    review_overdue_count: int,
    retention_expired_count: int,
    in_review_count: int,
    high_risk_count: int,
    vacant_role_count: int,
    ai_systems_without_owner_count: int,
    risk_owner_invalid_count: int,
    data_owner_invalid_count: int,
    uncovered_control_count: int,
    stale_control_count: int,
    overdue_corrective_action_count: int,
    overdue_audit_count: int,
    management_review_overdue: bool,
    incident_reports_overdue_count: int,
    open_incident_count: int,
    competence_gap_count: int,
    supplier_reviews_overdue_count: int,
    supplier_contracts_expiring_count: int,
    eu_ai_act_not_assessed: bool,
    possible_provider_count: int,
    objectives_falling_short_count: int,
    objective_measurements_overdue_count: int,
    changes_overdue_count: int,
    communications_overdue_count: int,
    concerns_awaiting_triage_count: int,
) -> list[AttentionItem]:
    """Actionable items, grouped by area and most urgent first. Zero-count
    items are dropped so the panel only ever shows things that need doing."""
    candidates = [
        AttentionItem(
            key="overdue_treatments",
            group=RISK_GROUP,
            label="Risk treatments overdue",
            count=overdue_count,
            severity="danger",
        ),
        AttentionItem(
            key="no_impact_assessment",
            group=RISK_GROUP,
            label="AI systems without a completed impact assessment",
            count=no_impact_assessment_count,
            severity="danger",
        ),
        AttentionItem(
            key="assessments_review_overdue",
            group=RISK_GROUP,
            label="Assessments overdue for annual review",
            count=review_overdue_count,
            severity="danger",
        ),
        AttentionItem(
            key="retention_expired",
            group=INVENTORY_GROUP,
            label="Archived systems past their retention date",
            count=retention_expired_count,
            severity="warning",
        ),
        AttentionItem(
            key="unassessed_ai_systems",
            group=RISK_GROUP,
            label="AI systems without a risk assessment",
            count=unassessed_count,
            severity="danger",
        ),
        AttentionItem(
            key="high_risk_assessments",
            group=RISK_GROUP,
            label="Assessments rated high risk",
            count=high_risk_count,
            severity="warning",
        ),
        AttentionItem(
            key="awaiting_review",
            group=PEOPLE_GROUP,
            label="Policies and procedures awaiting review",
            count=in_review_count,
            severity="warning",
        ),
        AttentionItem(
            key="vacant_governance_roles",
            group=PEOPLE_GROUP,
            label="Governance roles with no one assigned",
            count=vacant_role_count,
            severity="warning",
        ),
        AttentionItem(
            key="ai_systems_without_owner",
            group=INVENTORY_GROUP,
            label="AI systems without an active owner",
            count=ai_systems_without_owner_count,
            severity="warning",
        ),
        AttentionItem(
            key="risk_owner_not_a_real_account",
            group=RISK_GROUP,
            label="Risk items whose owner isn't an active account",
            count=risk_owner_invalid_count,
            severity="warning",
        ),
        AttentionItem(
            key="data_owner_not_a_real_account",
            group=INVENTORY_GROUP,
            label="Datasets whose owner isn't an active account",
            count=data_owner_invalid_count,
            severity="warning",
        ),
        AttentionItem(
            key="uncovered_framework_controls",
            group=COMPLIANCE_GROUP,
            label="Framework controls with no coverage",
            count=uncovered_control_count,
            severity="danger",
        ),
        AttentionItem(
            key="stale_framework_controls",
            group=COMPLIANCE_GROUP,
            label="Framework controls tagged but no longer current",
            count=stale_control_count,
            severity="warning",
        ),
        AttentionItem(
            key="eu_ai_act_not_assessed",
            group=COMPLIANCE_GROUP,
            label="EU AI Act applicability not yet assessed",
            # One assessment, not a count -- like management_review_overdue.
            count=1 if eu_ai_act_not_assessed else 0,
            severity="warning",
        ),
        AttentionItem(
            key="art25_possible_provider",
            group=COMPLIANCE_GROUP,
            label="Supplier AI systems you may have become the provider of (EU AI Act Art. 25)",
            count=possible_provider_count,
            severity="warning",
        ),
        AttentionItem(
            key="overdue_corrective_actions",
            group=INCIDENTS_GROUP,
            label="Corrective actions overdue",
            count=overdue_corrective_action_count,
            severity="danger",
        ),
        AttentionItem(
            key="audits_overdue",
            group=AUDIT_GROUP,
            label="Internal audits overdue",
            count=overdue_audit_count,
            severity="danger",
        ),
        AttentionItem(
            key="management_review_overdue",
            group=AUDIT_GROUP,
            label="Management review overdue",
            # One process, not a count -- 1 when it's overdue, otherwise
            # dropped like every other zero-count item.
            count=1 if management_review_overdue else 0,
            severity="danger",
        ),
        AttentionItem(
            key="incident_reports_overdue",
            group=INCIDENTS_GROUP,
            label="Serious incidents not reported to the authority in time",
            count=incident_reports_overdue_count,
            severity="danger",
        ),
        AttentionItem(
            key="open_incidents",
            group=INCIDENTS_GROUP,
            label="AI incidents still open",
            count=open_incident_count,
            severity="warning",
        ),
        AttentionItem(
            key="competence_gaps",
            group=PEOPLE_GROUP,
            label="Required training not completed or lapsed",
            count=competence_gap_count,
            severity="warning",
        ),
        AttentionItem(
            key="supplier_reviews_overdue",
            group=INVENTORY_GROUP,
            label="Supplier reviews overdue",
            count=supplier_reviews_overdue_count,
            severity="danger",
        ),
        AttentionItem(
            key="supplier_contracts_expiring",
            group=INVENTORY_GROUP,
            label="Supplier contracts ending soon or already ended",
            count=supplier_contracts_expiring_count,
            severity="warning",
        ),
        AttentionItem(
            key="objectives_off_track",
            group=OBJECTIVES_GROUP,
            label="AI objectives off track or past their target date",
            count=objectives_falling_short_count,
            severity="warning",
        ),
        AttentionItem(
            key="objective_measurements_overdue",
            group=OBJECTIVES_GROUP,
            label="AI objectives overdue for measurement",
            count=objective_measurements_overdue_count,
            severity="warning",
        ),
        AttentionItem(
            key="changes_overdue",
            group=PLANNING_GROUP,
            label="Planned changes to the management system past their date",
            count=changes_overdue_count,
            severity="warning",
        ),
        AttentionItem(
            key="communications_overdue",
            group=PLANNING_GROUP,
            label="Planned communications overdue",
            count=communications_overdue_count,
            severity="warning",
        ),
        AttentionItem(
            key="concerns_awaiting_triage",
            group=INCIDENTS_GROUP,
            label="Concerns raised by staff not yet acknowledged",
            count=concerns_awaiting_triage_count,
            severity="danger",
        ),
    ]
    return _order_attention([item for item in candidates if item.count > 0])


def _order_attention(items: list[AttentionItem]) -> list[AttentionItem]:
    """Each area's items together, so the panel can render one section per
    area. Areas with anything critical come first, then in
    ATTENTION_GROUP_ORDER; within an area, critical before warning, else in
    the order _attention lists them."""
    critical_groups = {item.group for item in items if item.severity == "danger"}

    def rank(indexed: tuple[int, AttentionItem]) -> tuple[bool, int, bool, int]:
        index, item = indexed
        return (
            item.group not in critical_groups,
            ATTENTION_GROUP_ORDER.index(item.group),
            item.severity != "danger",
            index,
        )

    return [item for _, item in sorted(enumerate(items), key=rank)]


def _my_risk_items(
    risk_assessments: list[RiskAssessment],
    rows_by_sheet: dict[int, list[SheetRow]],
    actor_id: int,
) -> list[MyRiskItem]:
    """Open risk items whose risk_owner cell matches the requesting user.
    risk_owner is stored as a stringified user id (see the DataGrid owner
    picker on RiskAssessment sheets) -- unassigned or legacy free-text
    owners (pre-dating real user accounts) simply never match."""
    owner_key = str(actor_id)
    items: list[MyRiskItem] = []
    for risk_assessment in risk_assessments:
        for row in rows_by_sheet.get(risk_assessment.sheet_id, []):
            if str(row.data.get("risk_owner", "")) != owner_key:
                continue
            if risk_scoring.is_treated(row.data.get("status")):
                continue
            items.append(
                MyRiskItem(
                    risk_assessment_id=risk_assessment.id,
                    row_id=row.id,
                    category=row.data.get("category"),
                    description=row.data.get("description"),
                    status=row.data.get("status"),
                    treatment_deadline=row.data.get("treatment_deadline"),
                    overdue=risk_scoring.is_overdue(row.data),
                )
            )
    # Overdue first, otherwise oldest deadline first (None sorts last).
    items.sort(key=lambda item: (not item.overdue, item.treatment_deadline or "9999-99-99"))
    return items


def _my_corrective_actions(
    corrective_actions: list[CorrectiveAction], actor_id: int, today: date
) -> list[MyCorrectiveActionItem]:
    """Open corrective actions assigned to the requesting user, same shape
    and sort as _my_risk_items."""
    items = [
        MyCorrectiveActionItem(
            id=ca.id,
            title=ca.title,
            status=ca.status,
            due_date=ca.due_date,
            overdue=corrective_action_service.is_overdue(ca.due_date, ca.status, today),
        )
        for ca in corrective_actions
        if ca.assignee_id == actor_id and ca.status != CorrectiveActionStatus.CLOSED
    ]
    items.sort(key=lambda item: (not item.overdue, item.due_date))
    return items


def _my_training(
    standings: list[tuple[CompetenceRequirement, list[PersonCompetence]]], actor_id: int
) -> list[MyTrainingItem]:
    """Requirements the requesting user hasn't met -- lapsed ones first,
    since those were once done and have quietly expired."""
    items = [
        MyTrainingItem(
            requirement_id=requirement.id,
            title=requirement.title,
            status=person.status,
            next_due=person.next_due,
        )
        for requirement, people in standings
        for person in people
        if person.user_id == actor_id and person.status != "current"
    ]
    items.sort(key=lambda item: (item.status != "expired", item.title))
    return items


def _invalid_owner_count(rows: list[SheetRow], column_key: str, valid_user_ids: set[int]) -> int:
    """Counts cells that are set but don't resolve to an *active* user -- a
    typo, or someone who has since been deactivated. A deactivated owner is
    worth surfacing because they can no longer sign anything off: they can't
    log in, and nobody else is allowed to approve in their place, so the record
    is stuck until it is reassigned. An unset owner is a separate, much noisier
    "not yet assigned" signal and is deliberately not counted here."""
    count = 0
    for row in rows:
        raw = row.data.get(column_key)
        if raw is None or not str(raw).strip():
            continue
        try:
            valid = int(raw) in valid_user_ids
        except (TypeError, ValueError):
            valid = False
        if not valid:
            count += 1
    return count


def get_summary(db: Session, actor_id: int) -> DashboardSummary:
    policies = policy_repository.list_all(db)
    procedures = procedure_repository.list_all(db)
    ai_system_rows = ai_system_inventory_service.list_rows(db)
    risk_assessments = risk_assessment_repository.list_all(db)

    # One query for every assessment's risk items instead of one per assessment.
    rows_by_sheet = sheet_repository.list_rows_for_sheets(
        db, [risk_assessment.sheet_id for risk_assessment in risk_assessments]
    )
    all_risk_rows: list[SheetRow] = [row for rows in rows_by_sheet.values() for row in rows]

    bands = risk_criteria_service.get_bands(db)

    high_risk_count = 0
    for risk_assessment in risk_assessments:
        rating = risk_analytics_service.overall_rating(
            rows_by_sheet.get(risk_assessment.sheet_id, [])
        )
        if rating is not None and risk_scoring.is_high_risk(rating, bands):
            high_risk_count += 1

    risk_tier_counts = Counter(
        str(row.data["risk_tier"]) if row.data.get("risk_tier") else "unspecified"
        for row in ai_system_rows
    )

    assessed_row_ids = {risk_assessment.ai_system_row_id for risk_assessment in risk_assessments}
    assessed_count = sum(1 for row in ai_system_rows if row.id in assessed_row_ids)

    # Impact assessment coverage: an AI system counts once it has at least one
    # COMPLETED impact assessment (drafts don't satisfy clause 8.4).
    impact_assessments = impact_assessment_repository.list_all(db)
    impact_assessed_row_ids = {
        assessment.ai_system_row_id
        for assessment in impact_assessments
        if assessment.status == ImpactAssessmentStatus.COMPLETED
    }
    impact_assessed_count = sum(1 for row in ai_system_rows if row.id in impact_assessed_row_ids)

    today = datetime.now(UTC).date()
    lifecycles = ai_system_lifecycle_repository.list_all(db)
    retention_expired_count = sum(
        1
        for lifecycle in lifecycles
        if ai_system_lifecycle_service.retention_expired(lifecycle, today)
    )
    # Retired policies and procedures are historical records, not part of the
    # active governance set -- they don't count towards coverage and they
    # aren't reviewed any more, the same way an archived AI system drops out of
    # the active estate.
    active_policies = [p for p in policies if p.status != RETIRED_STATUS]
    active_procedures = [p for p in procedures if p.status != RETIRED_STATUS]
    review_overdue_count = sum(
        1
        for record in [
            *impact_assessments,
            *risk_assessments,
            *active_policies,
            *active_procedures,
        ]
        if review_cadence.is_review_overdue(record.next_review_date, today)
    )

    risk_items = risk_analytics_service.summarize_rows(all_risk_rows, bands)
    in_review_count = sum(
        1 for record in [*active_policies, *active_procedures] if record.status == IN_REVIEW_STATUS
    )

    vacant_role_count = len(governance_role_service.vacant_roles(db))
    # Active only: a deactivated owner can't approve, so for accountability
    # purposes their id is no better than a typo or a null.
    valid_user_ids = {u.id for u in user_repository.list_all(db) if u.is_active}
    ai_systems_without_owner_count = sum(
        1 for lc in lifecycles if lc.owner_id not in valid_user_ids
    )
    risk_owner_invalid_count = _invalid_owner_count(all_risk_rows, "risk_owner", valid_user_ids)
    data_inventory_rows = data_inventory_service.list_rows(db)
    data_owner_invalid_count = _invalid_owner_count(
        data_inventory_rows, "data_owner", valid_user_ids
    )

    compliance = compliance_status_service.get_summary(db)
    compliance_groups = [
        compliance.iso_42001_clauses,
        compliance.iso_42001_annex_a,
        compliance.eu_ai_act,
    ]
    uncovered_control_count = sum(group.no_coverage for group in compliance_groups)
    stale_control_count = sum(group.partial for group in compliance_groups)

    corrective_actions = corrective_action_repository.list_all(db)
    overdue_corrective_action_count = sum(
        1
        for ca in corrective_actions
        if corrective_action_service.is_overdue(ca.due_date, ca.status, today)
    )

    audit_programs = internal_audit_repository.list_programs(db)
    audits_by_program = {
        program.id: internal_audit_repository.list_for_program(db, program.id)
        for program in audit_programs
    }
    overdue_audit_count = sum(
        1
        for program in audit_programs
        if internal_audit_service.is_overdue(program, audits_by_program[program.id], today)
    )

    management_review_settings = management_review_repository.get_settings(db)
    management_review_meetings = management_review_repository.list_meetings(db)
    management_review_overdue = management_review_service.is_overdue(
        management_review_settings, management_review_meetings, today
    )

    incidents = ai_incident_repository.list_all(db)
    incident_reports_overdue_count = sum(
        1 for incident in incidents if ai_incident_service.is_reporting_overdue(incident, today)
    )
    open_incident_count = sum(
        1 for incident in incidents if incident.status != AIIncidentStatus.RESOLVED
    )

    competence_standings = competence_service.standings(db, today)
    competence_gap_count = sum(
        competence_service.gap_count(people) for _, people in competence_standings
    )

    supplier_review_dates = supplier_service.review_dates_by_supplier(db)
    supplier_standings = [
        supplier_service.standing(supplier, supplier_review_dates[supplier.id], today)
        for supplier in supplier_repository.list_all(db)
    ]
    supplier_reviews_overdue_count = sum(1 for s in supplier_standings if s.review_overdue)
    supplier_contracts_expiring_count = sum(
        1 for s in supplier_standings if s.contract_status is not None
    )
    objective_counts = objective_service.attention_counts(db, today)

    return DashboardSummary(
        policies=StatusCounts(
            total=len(policies), by_status=dict(Counter(p.status for p in policies))
        ),
        procedures=StatusCounts(
            total=len(procedures), by_status=dict(Counter(p.status for p in procedures))
        ),
        ai_systems=AISystemSummary(total=len(ai_system_rows), by_risk_tier=dict(risk_tier_counts)),
        risk_assessments=RiskAssessmentSummary(
            total=len(risk_assessments),
            by_status=dict(Counter(ra.status for ra in risk_assessments)),
            high_risk_count=high_risk_count,
        ),
        risk_items=risk_items,
        coverage=CoverageSummary(
            ai_systems_total=len(ai_system_rows),
            ai_systems_assessed=assessed_count,
            ai_systems_impact_assessed=impact_assessed_count,
            assessments_review_overdue=review_overdue_count,
            policies_total=len(active_policies),
            policies_approved=sum(1 for p in active_policies if p.status == APPROVED_STATUS),
            procedures_total=len(active_procedures),
            procedures_approved=sum(1 for p in active_procedures if p.status == APPROVED_STATUS),
        ),
        compliance=compliance,
        attention=_attention(
            overdue_count=risk_items.overdue_count,
            unassessed_count=len(ai_system_rows) - assessed_count,
            no_impact_assessment_count=len(ai_system_rows) - impact_assessed_count,
            review_overdue_count=review_overdue_count,
            retention_expired_count=retention_expired_count,
            in_review_count=in_review_count,
            high_risk_count=high_risk_count,
            vacant_role_count=vacant_role_count,
            ai_systems_without_owner_count=ai_systems_without_owner_count,
            risk_owner_invalid_count=risk_owner_invalid_count,
            data_owner_invalid_count=data_owner_invalid_count,
            uncovered_control_count=uncovered_control_count,
            stale_control_count=stale_control_count,
            overdue_corrective_action_count=overdue_corrective_action_count,
            overdue_audit_count=overdue_audit_count,
            management_review_overdue=management_review_overdue,
            incident_reports_overdue_count=incident_reports_overdue_count,
            open_incident_count=open_incident_count,
            competence_gap_count=competence_gap_count,
            supplier_reviews_overdue_count=supplier_reviews_overdue_count,
            supplier_contracts_expiring_count=supplier_contracts_expiring_count,
            eu_ai_act_not_assessed=compliance.eu_ai_act_scope == "not_assessed",
            possible_provider_count=supplier_service.possible_provider_count(db),
            objectives_falling_short_count=objective_counts.falling_short,
            objective_measurements_overdue_count=objective_counts.measurement_overdue,
            changes_overdue_count=change_service.overdue_count(db, today),
            communications_overdue_count=communication_service.overdue_count(db, today),
            concerns_awaiting_triage_count=concern_service.standing(
                db, today
            ).awaiting_triage_count,
        ),
        matrix=risk_analytics_service.matrix_cells(all_risk_rows),
        criteria=risk_criteria_service.get_criteria(db),
        my_risk_items=_my_risk_items(risk_assessments, rows_by_sheet, actor_id),
        my_corrective_actions=_my_corrective_actions(corrective_actions, actor_id, today),
        my_training=_my_training(competence_standings, actor_id),
        pending_approvals=pending_approvals_service.get_pending_approvals(
            db,
            actor_id,
            policies=policies,
            procedures=procedures,
            lifecycles=lifecycles,
            ai_system_rows=ai_system_rows,
            risk_assessments=risk_assessments,
            impact_assessments=impact_assessments,
            data_inventory_rows=data_inventory_rows,
            data_inventory_records=data_inventory_service.list_records(db),
        ),
    )
