"""Everything currently waiting on a specific user's approval, across every
entity type that has an approval gate: Policy/Procedure (CAIGO), AI System
deployment/retirement (CAIGO), and Risk/Impact Assessment (AI System Owner,
then CAIGO). Powers the dashboard's "Pending My Approval" panel.

Each check mirrors the actual gate in the corresponding service exactly, so
this list never shows something the user would in fact be rejected for
trying to approve -- see policy_service.approve_policy,
ai_system_lifecycle_service.approve_deployment/approve_retirement, and
risk_assessment_service/impact_assessment_service's approve_owner_stage/
approve_caigo_stage for the source of truth each check reproduces."""

from sqlalchemy.orm import Session

from app.core.lifecycle_stages import LifecycleStage
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.models.impact_assessment import ImpactAssessmentStatus
from app.models.policy import PolicyStatus
from app.models.procedure import ProcedureStatus
from app.models.risk_assessment import RiskAssessmentStatus
from app.models.sheet import SheetRow
from app.repositories import (
    ai_system_lifecycle_repository,
    audit_log_repository,
    impact_assessment_repository,
    policy_repository,
    procedure_repository,
    risk_assessment_repository,
)
from app.schemas.dashboard import PendingApprovalItem
from app.services import ai_system_inventory_service, governance_role_service

SUBMITTED = "submitted_for_review"
CAIGO_STAGE_LABEL = "Awaiting your approval as Chief AI Governance Officer"
OWNER_STAGE_LABEL = "Awaiting your approval as this AI system's owner"


def _ai_system_name(ai_system_rows_by_id: dict[int, SheetRow], ai_system_row_id: int) -> str:
    row = ai_system_rows_by_id.get(ai_system_row_id)
    name = row.data.get("name") if row is not None else None
    return str(name) if name else f"AI System #{ai_system_row_id}"


def _caigo_stage_items(
    db: Session,
    user_id: int,
    entity_type: str,
    audit_entity_type: str,
    candidate_ids: list[int],
    title_by_id: dict[int, str],
) -> list[PendingApprovalItem]:
    """Shared shape for every "pending_caigo_approval"-style stage: keep a
    candidate only if it has actually been submitted, and the submitter
    wasn't this same user (audit_service.require_different_approver's rule,
    reproduced here as a filter rather than an exception)."""
    latest = audit_log_repository.latest_entry_by_entity(
        db, audit_entity_type, candidate_ids, [SUBMITTED]
    )
    items = []
    for entity_id in candidate_ids:
        entry = latest.get(entity_id)
        if entry is not None and entry.actor_id != user_id:
            items.append(
                PendingApprovalItem(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title_by_id[entity_id],
                    stage_label=CAIGO_STAGE_LABEL,
                    submitted_at=entry.timestamp,
                )
            )
    return items


def get_pending_approvals(db: Session, user_id: int) -> list[PendingApprovalItem]:
    items: list[PendingApprovalItem] = []
    is_caigo = governance_role_service.is_caigo(db, user_id)
    ai_system_rows_by_id = {row.id: row for row in ai_system_inventory_service.list_rows(db)}

    if is_caigo:
        policies = [
            p for p in policy_repository.list_all(db) if p.status == PolicyStatus.IN_REVIEW
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "Policy",
            "Policy",
            [p.id for p in policies],
            {p.id: p.title for p in policies},
        )

        procedures = [
            p for p in procedure_repository.list_all(db) if p.status == ProcedureStatus.IN_REVIEW
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "Procedure",
            "Procedure",
            [p.id for p in procedures],
            {p.id: p.title for p in procedures},
        )

    lifecycles = ai_system_lifecycle_repository.list_all(db)

    if is_caigo:
        deployment_candidates = [
            lc
            for lc in lifecycles
            if lc.current_stage == LifecycleStage.VERIFICATION_AND_VALIDATION
            and lc.deployment_approved_by is None
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "AISystemDeployment",
            "AISystemDeploymentApproval",
            [lc.ai_system_row_id for lc in deployment_candidates],
            {
                lc.ai_system_row_id: _ai_system_name(ai_system_rows_by_id, lc.ai_system_row_id)
                for lc in deployment_candidates
            },
        )

        retirement_candidates = [
            lc
            for lc in lifecycles
            if lc.current_stage == LifecycleStage.OPERATION_AND_MONITORING
            and lc.retirement_approved_by is None
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "AISystemRetirement",
            "AISystemRetirementApproval",
            [lc.ai_system_row_id for lc in retirement_candidates],
            {
                lc.ai_system_row_id: _ai_system_name(ai_system_rows_by_id, lc.ai_system_row_id)
                for lc in retirement_candidates
            },
        )

    lifecycle_by_row: dict[int, AISystemLifecycle] = {lc.ai_system_row_id: lc for lc in lifecycles}

    def owner_stage_item(entity_type: str, entity_id: int, ai_system_row_id: int) -> None:
        lc = lifecycle_by_row.get(ai_system_row_id)
        if lc is not None and lc.owner_id == user_id:
            items.append(
                PendingApprovalItem(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=_ai_system_name(ai_system_rows_by_id, ai_system_row_id),
                    stage_label=OWNER_STAGE_LABEL,
                    submitted_at=None,
                )
            )

    risk_assessments = risk_assessment_repository.list_all(db)
    for ra in risk_assessments:
        if ra.status == RiskAssessmentStatus.PENDING_OWNER_APPROVAL:
            owner_stage_item("RiskAssessment", ra.id, ra.ai_system_row_id)

    if is_caigo:
        caigo_pending_ras = [
            ra
            for ra in risk_assessments
            if ra.status == RiskAssessmentStatus.PENDING_CAIGO_APPROVAL
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "RiskAssessment",
            "RiskAssessmentCaigoApproval",
            [ra.id for ra in caigo_pending_ras],
            {
                ra.id: _ai_system_name(ai_system_rows_by_id, ra.ai_system_row_id)
                for ra in caigo_pending_ras
            },
        )

    impact_assessments = impact_assessment_repository.list_all(db)
    for ia in impact_assessments:
        if ia.status == ImpactAssessmentStatus.PENDING_OWNER_APPROVAL:
            owner_stage_item("ImpactAssessment", ia.id, ia.ai_system_row_id)

    if is_caigo:
        caigo_pending_ias = [
            ia
            for ia in impact_assessments
            if ia.status == ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL
        ]
        items += _caigo_stage_items(
            db,
            user_id,
            "ImpactAssessment",
            "ImpactAssessmentCaigoApproval",
            [ia.id for ia in caigo_pending_ias],
            {
                ia.id: _ai_system_name(ai_system_rows_by_id, ia.ai_system_row_id)
                for ia in caigo_pending_ias
            },
        )

    # Most recently submitted first; items with no timestamp (the
    # owner-approval stage, which has no separate "submitted" audit entry
    # of its own) sort last.
    items.sort(
        key=lambda item: item.submitted_at.timestamp() if item.submitted_at else float("-inf"),
        reverse=True,
    )
    return items
