"""AI system impact assessments (ISO 42001 clause 8.4 / Annex A.5, structured
per ISO/IEC 42005). Each assessment is scoped to one AI system
(ai_system_row_id, same sheet_rows FK RiskAssessment uses) rather than to a
single Risk Assessment run -- a system can be re-assessed several times, and
every Risk Assessment for that system shares the same impact history.

Each assessment carries a fixed scorecard of the eight ISO 42005 impact
factors -- benefits/harms/criteria written up by a human, score assigned
manually for now (a future pass can derive it automatically from the
benefits/harms/criteria text instead)."""

from sqlalchemy.orm import Session

from app.core.concurrency import conflict_on_duplicate
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.impact_factors import IMPACT_FACTORS
from app.models.impact_assessment import ImpactAssessment, ImpactAssessmentStatus
from app.models.impact_factor_assessment import ImpactFactorAssessment
from app.repositories import (
    impact_assessment_repository,
    impact_factor_assessment_repository,
    risk_assessment_repository,
    sheet_repository,
)
from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.services import (
    ai_system_inventory_service,
    approval_chain_service,
    audit_service,
    evidence_service,
    framework_service,
)

ENTITY_TYPE = "ImpactAssessment"

OWNER_APPROVAL_ENTITY_TYPE = "ImpactAssessmentOwnerApproval"
CAIGO_APPROVAL_ENTITY_TYPE = "ImpactAssessmentCaigoApproval"

ONE_PER_AI_SYSTEM_MESSAGE = (
    "This AI system already has an impact assessment. Update it instead of "
    "creating another."
)

_PRE_APPROVAL_STATUSES = {ImpactAssessmentStatus.DRAFT}
_GATED_STATUSES = {
    ImpactAssessmentStatus.PENDING_OWNER_APPROVAL,
    ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL,
    ImpactAssessmentStatus.COMPLETED,
}

MIN_SCORE = 1
MAX_SCORE = 5


def _get_or_raise(db: Session, impact_assessment_id: int) -> ImpactAssessment:
    impact_assessment = impact_assessment_repository.get(db, impact_assessment_id)
    if impact_assessment is None:
        raise NotFoundError("ImpactAssessment", impact_assessment_id)
    return impact_assessment


def _validate_ai_system_row(db: Session, ai_system_row_id: int) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None or row.sheet_id != inventory_sheet.id:
        raise NotFoundError("AISystemRow", ai_system_row_id)


def list_all(db: Session) -> list[ImpactAssessment]:
    return impact_assessment_repository.list_all(db)


def list_for_ai_system(db: Session, ai_system_row_id: int) -> list[ImpactAssessment]:
    return impact_assessment_repository.list_for_ai_system(db, ai_system_row_id)


def get_for_ai_system(db: Session, ai_system_row_id: int) -> ImpactAssessment | None:
    """An AI system has at most one impact assessment -- the yearly review
    updates that record rather than adding another."""
    existing = list_for_ai_system(db, ai_system_row_id)
    return existing[0] if existing else None


def list_for_risk_assessment(db: Session, risk_assessment_id: int) -> list[ImpactAssessment]:
    """The risk-assessment detail page's view of its system's impact
    assessment -- at most one, returned as a list so the caller doesn't need
    a separate empty case."""
    risk_assessment = risk_assessment_repository.get(db, risk_assessment_id)
    if risk_assessment is None:
        raise NotFoundError("RiskAssessment", risk_assessment_id)
    return list_for_ai_system(db, risk_assessment.ai_system_row_id)


def get(db: Session, impact_assessment_id: int) -> ImpactAssessment:
    return _get_or_raise(db, impact_assessment_id)


def get_factors(db: Session, impact_assessment_id: int) -> list[ImpactFactorAssessment]:
    return impact_factor_assessment_repository.list_for_assessment(db, impact_assessment_id)


def create_for_ai_system(
    db: Session, ai_system_row_id: int, data: ImpactAssessmentCreate, actor_id: int | None
) -> ImpactAssessment:
    _validate_ai_system_row(db, ai_system_row_id)

    # One per AI system: re-assessing means revisiting this record and
    # re-completing it, which re-stamps the yearly review date.
    if get_for_ai_system(db, ai_system_row_id) is not None:
        raise ConflictError(ONE_PER_AI_SYSTEM_MESSAGE)

    impact_assessment = ImpactAssessment(
        ai_system_row_id=ai_system_row_id,
        assessor_id=data.assessor_id,
        assessment_date=data.assessment_date,
    )
    # The check above runs in a transaction of its own, so a simultaneous
    # request can pass it too; the unique constraint decides which one lands.
    with conflict_on_duplicate(db, ONE_PER_AI_SYSTEM_MESSAGE):
        impact_assessment = impact_assessment_repository.create(db, impact_assessment)
    impact_factor_assessment_repository.create_all_factors(db, impact_assessment.id)
    audit_service.log(
        db, ENTITY_TYPE, impact_assessment.id, "created", actor_id,
        {"ai_system_row_id": ai_system_row_id},
    )
    return impact_assessment


def update(
    db: Session, impact_assessment_id: int, data: ImpactAssessmentUpdate, actor_id: int | None
) -> ImpactAssessment:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    changes = data.model_dump(exclude_unset=True)
    if "status" in changes and (
        changes["status"] in _GATED_STATUSES
        or impact_assessment.status not in _PRE_APPROVAL_STATUSES
    ):
        raise ValidationError(
            "Use the submit/approve endpoints to move an impact assessment through "
            "owner and CAIGO approval -- status can't be set directly once it's "
            "in the approval pipeline."
        )
    assessed_fields_changed = any(
        field != "status" and getattr(impact_assessment, field) != value
        for field, value in changes.items()
    )
    for field, value in changes.items():
        setattr(impact_assessment, field, value)
    if assessed_fields_changed:
        _withdraw_approval(db, impact_assessment, actor_id)

    impact_assessment = impact_assessment_repository.save(db, impact_assessment)
    audit_service.log(db, ENTITY_TYPE, impact_assessment_id, "updated", actor_id, changes)
    return impact_assessment


def _withdraw_approval(
    db: Session, impact_assessment: ImpactAssessment, actor_id: int | None
) -> None:
    """Changing what was assessed sends the assessment back to draft -- see
    approval_chain_service.revert_to_draft."""
    approval_chain_service.revert_to_draft(
        db,
        impact_assessment,
        actor_id,
        draft_status=ImpactAssessmentStatus.DRAFT,
        caigo_approval_entity_type=CAIGO_APPROVAL_ENTITY_TYPE,
    )


def submit_for_owner_approval(
    db: Session, impact_assessment_id: int, actor_id: int | None
) -> ImpactAssessment:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    approval_chain_service.submit_for_owner_approval(
        db,
        impact_assessment,
        actor_id,
        entity_label="ImpactAssessment",
        owner_approval_entity_type=OWNER_APPROVAL_ENTITY_TYPE,
        caigo_approval_entity_type=CAIGO_APPROVAL_ENTITY_TYPE,
        pre_approval_statuses=_PRE_APPROVAL_STATUSES,
        pre_approval_label="draft",
        pending_owner_status=ImpactAssessmentStatus.PENDING_OWNER_APPROVAL,
        pending_caigo_status=ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL,
    )
    impact_assessment = impact_assessment_repository.save(db, impact_assessment)
    audit_service.log(db, ENTITY_TYPE, impact_assessment_id, "submitted_for_review", actor_id)
    return impact_assessment


def approve_owner_stage(
    db: Session, impact_assessment_id: int, actor_id: int | None
) -> ImpactAssessment:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    approval_chain_service.approve_owner_stage(
        db,
        impact_assessment,
        actor_id,
        entity_label="ImpactAssessment",
        owner_approval_entity_type=OWNER_APPROVAL_ENTITY_TYPE,
        caigo_approval_entity_type=CAIGO_APPROVAL_ENTITY_TYPE,
        pending_owner_status=ImpactAssessmentStatus.PENDING_OWNER_APPROVAL,
        pending_caigo_status=ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL,
    )
    return impact_assessment_repository.save(db, impact_assessment)


def approve_caigo_stage(
    db: Session, impact_assessment_id: int, actor_id: int | None
) -> ImpactAssessment:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    approval_chain_service.approve_caigo_stage(
        db,
        impact_assessment,
        actor_id,
        entity_label="ImpactAssessment",
        caigo_approval_entity_type=CAIGO_APPROVAL_ENTITY_TYPE,
        pending_caigo_status=ImpactAssessmentStatus.PENDING_CAIGO_APPROVAL,
        completed_status=ImpactAssessmentStatus.COMPLETED,
    )
    return impact_assessment_repository.save(db, impact_assessment)


def has_completed_for_ai_system(db: Session, ai_system_row_id: int) -> bool:
    """Whether this AI system has an impact assessment signed off -- the
    precondition for opening a risk assessment against it."""
    return any(
        assessment.status == ImpactAssessmentStatus.COMPLETED
        for assessment in list_for_ai_system(db, ai_system_row_id)
    )


def update_factor(
    db: Session,
    impact_assessment_id: int,
    factor: str,
    benefits: str | None,
    harms: str | None,
    criteria: str | None,
    score: int | None,
    actor_id: int | None,
) -> ImpactFactorAssessment:
    if factor not in IMPACT_FACTORS:
        raise ValidationError(f"Unknown impact factor: {factor}")
    if score is not None and not (MIN_SCORE <= score <= MAX_SCORE):
        raise ValidationError(f"Score must be between {MIN_SCORE} and {MAX_SCORE}")
    _get_or_raise(db, impact_assessment_id)

    factor_assessment = impact_factor_assessment_repository.get_by_assessment_and_factor(
        db, impact_assessment_id, factor
    )
    if factor_assessment is None:
        raise NotFoundError("ImpactFactorAssessment", impact_assessment_id)

    changed = (
        factor_assessment.benefits != benefits
        or factor_assessment.harms != harms
        or factor_assessment.criteria != criteria
        or factor_assessment.score != score
    )
    factor_assessment.benefits = benefits
    factor_assessment.harms = harms
    factor_assessment.criteria = criteria
    factor_assessment.score = score
    factor_assessment = impact_factor_assessment_repository.save(db, factor_assessment)
    audit_service.log(
        db, ENTITY_TYPE, impact_assessment_id, "factor_updated", actor_id,
        {"factor": factor, "score": score},
    )
    # The scorecard is the assessment -- an approval of it can't outlive a
    # change to a factor's score or write-up.
    if changed:
        impact_assessment = _get_or_raise(db, impact_assessment_id)
        _withdraw_approval(db, impact_assessment, actor_id)
        impact_assessment_repository.save(db, impact_assessment)
    return factor_assessment


def delete(db: Session, impact_assessment_id: int, actor_id: int | None) -> None:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    # ISO 42001 8.4 sequencing is enforced when a risk assessment is created
    # (create_risk_assessment), so it has to be maintained here too -- deleting
    # this would otherwise leave the risk assessment standing on an impact
    # assessment that no longer exists. ai_system_inventory_service.delete_row
    # deletes the risk assessment first, so the cascade still gets through.
    if risk_assessment_repository.get_for_ai_system(
        db, impact_assessment.ai_system_row_id
    ) is not None:
        raise ConflictError(
            "The risk assessment for this AI system was built on this impact "
            "assessment; delete that first."
        )

    impact_factor_assessment_repository.delete_for_assessment(db, impact_assessment_id)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, impact_assessment_id)
    framework_service.delete_tags(db, ENTITY_TYPE, impact_assessment_id)
    impact_assessment_repository.delete(db, impact_assessment)
    audit_service.log(db, ENTITY_TYPE, impact_assessment_id, "deleted", actor_id)
