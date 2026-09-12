"""Stage gates: what must be true before an AI system leaves a stage.

Every requirement is computed from the governance work already recorded
elsewhere -- assessments, evidence, inventory fields, risk items -- rather
than being a checkbox someone ticks. That way a gate cannot pass while the
underlying artefact is missing, and it re-opens by itself if the artefact is
later deleted.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import review_cadence, risk_scoring
from app.core.document_types import DOCUMENT_TYPE_LABELS, DocumentType
from app.core.lifecycle_stages import LifecycleStage
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.repositories import evidence_repository, sheet_repository
from app.services import (
    data_inventory_service,
    impact_assessment_service,
    risk_criteria_service,
)

AI_SYSTEM_ENTITY_TYPE = "AISystem"

# Everything an inventory entry must say about a system before it can be
# built -- the A.4 resource fields plus the basics.
REQUIRED_INVENTORY_FIELDS: dict[str, str] = {
    "name": "Name",
    "description": "Description",
    "purpose": "Purpose",
    "risk_tier": "Risk Tier",
    "resource_documentation": "Resource Documentation",
    "data_resources": "Data Resources",
    "tooling_frameworks": "Tooling & Frameworks",
    "compute_infrastructure": "Compute Infrastructure",
    "hosting_environment": "Hosting Environment",
    "development_team": "Development Team",
    "oversight_roles": "Oversight Roles",
}


@dataclass
class GateRequirement:
    key: str
    label: str
    satisfied: bool
    detail: str


def _document_requirement(
    db: Session, ai_system_row_id: int, document_type: DocumentType
) -> GateRequirement:
    documents = evidence_repository.list_for_entity(
        db, AI_SYSTEM_ENTITY_TYPE, ai_system_row_id, document_type
    )
    label = DOCUMENT_TYPE_LABELS[document_type]
    return GateRequirement(
        key=str(document_type),
        label=f"{label} uploaded",
        satisfied=bool(documents),
        detail=(
            f"{documents[0].filename} attached"
            if documents
            else f"Upload a {label.lower()} for this AI system."
        ),
    )


def _inception_requirements(
    db: Session, ai_system_row_id: int, lifecycle: AISystemLifecycle
) -> list[GateRequirement]:
    # Imported here rather than at module scope: risk_assessment_service
    # imports this module's siblings, and a top-level import is circular.
    from app.services import risk_assessment_service

    impact = impact_assessment_service.get_for_ai_system(db, ai_system_row_id)
    impact_done = impact is not None and impact.status == "completed"

    risk_assessment = risk_assessment_service.get_for_ai_system(db, ai_system_row_id)
    risk_item_count = (
        len(sheet_repository.list_rows(db, risk_assessment.sheet_id))
        if risk_assessment is not None
        else 0
    )

    has_owner = lifecycle.owner_id is not None

    return [
        GateRequirement(
            key="ai_system_owner",
            label="AI System Owner assigned",
            satisfied=has_owner,
            detail=(
                "Assigned."
                if has_owner
                else "Assign the owner accountable for this system -- they approve "
                "its impact and risk assessments."
            ),
        ),
        GateRequirement(
            key="impact_assessment_completed",
            label="Impact assessment completed",
            satisfied=impact_done,
            detail=(
                "Completed."
                if impact_done
                else "Perform the impact assessment and mark it completed."
            ),
        ),
        GateRequirement(
            key="risk_assessment_performed",
            label="Risk assessment performed",
            satisfied=risk_item_count > 0,
            detail=(
                f"{risk_item_count} risk item(s) recorded."
                if risk_item_count
                else "Create the risk assessment and record at least one risk item."
            ),
        ),
    ]


def _development_requirements(db: Session, ai_system_row_id: int) -> list[GateRequirement]:
    row = sheet_repository.get_row(db, ai_system_row_id)
    data = row.data if row is not None else {}
    missing = [
        field_label
        for key, field_label in REQUIRED_INVENTORY_FIELDS.items()
        if not str(data.get(key) or "").strip()
    ]

    linked_datasets = [
        dataset
        for dataset in data_inventory_service.list_rows(db)
        if str(dataset.data.get("ai_system_row_id") or "") == str(ai_system_row_id)
    ]
    # An unreviewed draft shouldn't carry a stage gate: the dataset entry has
    # to have been through its Data Owner and CAIGO review to count here.
    approved_ids = data_inventory_service.approved_row_ids(db)
    approved_datasets = [
        dataset for dataset in linked_datasets if dataset.id in approved_ids
    ]

    return [
        GateRequirement(
            key="inventory_complete",
            label="AI system details recorded in the inventory",
            satisfied=not missing,
            detail=(
                "All required fields are filled in."
                if not missing
                else f"Still empty: {', '.join(missing)}."
            ),
        ),
        GateRequirement(
            key="data_inventory_entry",
            label="Approved datasets recorded in the Data Inventory",
            satisfied=bool(approved_datasets),
            detail=(
                f"{len(approved_datasets)} of {len(linked_datasets)} linked "
                "dataset(s) approved."
                if linked_datasets
                else "Add at least one Data Inventory entry linked to this AI system."
            ),
        ),
    ]


def _untreated_high_risks(db: Session, ai_system_row_id: int) -> list[str]:
    """Open risk items whose residual score still lands in the High band."""
    from app.services import risk_assessment_service

    risk_assessment = risk_assessment_service.get_for_ai_system(db, ai_system_row_id)
    if risk_assessment is None:
        return []

    bands = risk_criteria_service.get_bands(db)
    flagged = []
    for row in sheet_repository.list_rows(db, risk_assessment.sheet_id):
        if risk_scoring.is_treated(row.data.get("status")):
            continue
        score = row.data.get("residual_risk_score") or row.data.get("inherent_risk_score")
        if score is not None and risk_scoring.is_high_risk(float(score), bands):
            flagged.append(str(row.data.get("category") or f"Risk item #{row.id}"))
    return flagged


def _validation_requirements(
    db: Session, ai_system_row_id: int, lifecycle: AISystemLifecycle
) -> list[GateRequirement]:
    high_risks = _untreated_high_risks(db, ai_system_row_id)
    has_deployment_record = all(
        [
            lifecycle.deployment_environment,
            lifecycle.deployment_version,
            lifecycle.deployed_at,
        ]
    )

    return [
        _document_requirement(db, ai_system_row_id, DocumentType.VALIDATION_REPORT),
        GateRequirement(
            key="deployment_approved",
            label="Release approved",
            satisfied=lifecycle.deployment_approved_by is not None,
            detail=(
                "Approved."
                if lifecycle.deployment_approved_by is not None
                else "Request approval, then have a different admin approve the release."
            ),
        ),
        GateRequirement(
            key="no_untreated_high_risks",
            label="No untreated high risks",
            satisfied=not high_risks,
            detail=(
                "No open risk item scores in the High band."
                if not high_risks
                else f"Still open and high: {', '.join(high_risks)}."
            ),
        ),
        GateRequirement(
            key="deployment_record",
            label="Deployment record captured",
            satisfied=bool(has_deployment_record),
            detail=(
                f"{lifecycle.deployment_environment} · {lifecycle.deployment_version} "
                f"· {lifecycle.deployed_at}"
                if has_deployment_record
                else "Record the environment, version and deployment date."
            ),
        ),
    ]


def _deployment_requirements(
    db: Session, ai_system_row_id: int, lifecycle: AISystemLifecycle
) -> list[GateRequirement]:
    from app.services import risk_assessment_service

    today = datetime.now(UTC).date()
    impact = impact_assessment_service.get_for_ai_system(db, ai_system_row_id)
    risk_assessment = risk_assessment_service.get_for_ai_system(db, ai_system_row_id)
    overdue = [
        name
        for name, assessment in (("Impact", impact), ("Risk", risk_assessment))
        if assessment is not None
        and review_cadence.is_review_overdue(assessment.next_review_date, today)
    ]

    return [
        _document_requirement(db, ai_system_row_id, DocumentType.MONITORING_PLAN),
        GateRequirement(
            key="monitoring_owner",
            label="Monitoring owner assigned",
            satisfied=lifecycle.monitoring_owner_id is not None,
            detail=(
                "Assigned."
                if lifecycle.monitoring_owner_id is not None
                else "Name the person accountable for monitoring this system in production."
            ),
        ),
        GateRequirement(
            key="reviews_current",
            label="Impact and risk assessments up to date",
            satisfied=not overdue,
            detail=(
                "Both are within their yearly review date."
                if not overdue
                else f"Overdue for review: {', '.join(overdue)}."
            ),
        ),
        GateRequirement(
            key="incident_escalation_path",
            label="Incident escalation path recorded",
            satisfied=bool((lifecycle.incident_escalation_path or "").strip()),
            detail=(
                "Recorded."
                if (lifecycle.incident_escalation_path or "").strip()
                else "Record who is contacted, and how, when this system misbehaves."
            ),
        ),
    ]


def _operation_requirements(lifecycle: AISystemLifecycle) -> list[GateRequirement]:
    """Retiring a system is a decision, not a drift -- it needs a stated
    reason and a second pair of eyes."""
    reason = (lifecycle.retirement_reason or "").strip()
    return [
        GateRequirement(
            key="retirement_reason",
            label="Retirement reason recorded",
            satisfied=bool(reason),
            detail=(
                "Recorded."
                if reason
                else "Say why this system is being retired before starting retirement."
            ),
        ),
        GateRequirement(
            key="retirement_approved",
            label="Retirement approved",
            satisfied=lifecycle.retirement_approved_by is not None,
            detail=(
                "Approved."
                if lifecycle.retirement_approved_by is not None
                else "Request approval, then have a different admin approve the retirement."
            ),
        ),
    ]


def _retirement_requirements(
    db: Session, ai_system_row_id: int, lifecycle: AISystemLifecycle
) -> list[GateRequirement]:
    """What must be true before the system's record moves to the archive."""
    return [
        _document_requirement(db, ai_system_row_id, DocumentType.RETIREMENT_SIGNOFF),
        GateRequirement(
            key="retention_until",
            label="Retention period set",
            satisfied=lifecycle.retention_until is not None,
            detail=(
                f"Kept until {lifecycle.retention_until}."
                if lifecycle.retention_until is not None
                else "Set how long this system's record must be kept before it can be deleted."
            ),
        ),
    ]


def gate_requirements(
    db: Session, ai_system_row_id: int, lifecycle: AISystemLifecycle
) -> list[GateRequirement]:
    """What must be satisfied to leave the stage this system is currently in.
    At Retirement -- the last stage -- these are the requirements to archive
    the record instead."""
    stage = lifecycle.current_stage

    if stage == LifecycleStage.INCEPTION:
        return _inception_requirements(db, ai_system_row_id, lifecycle)
    if stage == LifecycleStage.DESIGN:
        return [_document_requirement(db, ai_system_row_id, DocumentType.DESIGN_DOCUMENT)]
    if stage == LifecycleStage.DEVELOPMENT:
        return _development_requirements(db, ai_system_row_id)
    if stage == LifecycleStage.VERIFICATION_AND_VALIDATION:
        return _validation_requirements(db, ai_system_row_id, lifecycle)
    if stage == LifecycleStage.DEPLOYMENT:
        return _deployment_requirements(db, ai_system_row_id, lifecycle)
    if stage == LifecycleStage.OPERATION_AND_MONITORING:
        return _operation_requirements(lifecycle)
    if stage == LifecycleStage.RETIREMENT and lifecycle.archived_at is None:
        return _retirement_requirements(db, ai_system_row_id, lifecycle)
    return []


def unmet(requirements: list[GateRequirement]) -> list[GateRequirement]:
    return [requirement for requirement in requirements if not requirement.satisfied]
