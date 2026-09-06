from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import review_cadence
from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.impact_assessment import ImpactAssessment
from app.schemas.impact_assessment import (
    ImpactAssessmentCreate,
    ImpactAssessmentForSystemCreate,
    ImpactAssessmentRead,
    ImpactAssessmentUpdate,
    ImpactFactorAssessmentRead,
    ImpactFactorAssessmentUpdate,
)
from app.services import framework_service, impact_assessment_service

risk_assessments_router = APIRouter(prefix="/risk-assessments", tags=["impact-assessments"])
router = APIRouter(prefix="/impact-assessments", tags=["impact-assessments"])


def _to_read(db: Session, impact_assessment: ImpactAssessment) -> ImpactAssessmentRead:
    framework_tags = framework_service.get_tags(db, "ImpactAssessment", impact_assessment.id)
    factors = impact_assessment_service.get_factors(db, impact_assessment.id)
    return ImpactAssessmentRead(
        id=impact_assessment.id,
        ai_system_row_id=impact_assessment.ai_system_row_id,
        status=impact_assessment.status,
        assessor_id=impact_assessment.assessor_id,
        assessment_date=impact_assessment.assessment_date,
        next_review_date=impact_assessment.next_review_date,
        review_overdue=review_cadence.is_review_overdue(
            impact_assessment.next_review_date, datetime.now(UTC).date()
        ),
        system_description=impact_assessment.system_description,
        intended_purpose=impact_assessment.intended_purpose,
        foreseeable_misuse=impact_assessment.foreseeable_misuse,
        data_and_model_info=impact_assessment.data_and_model_info,
        deployment_environment=impact_assessment.deployment_environment,
        affected_interested_parties=impact_assessment.affected_interested_parties,
        human_oversight_role=impact_assessment.human_oversight_role,
        conclusion=impact_assessment.conclusion,
        owner_approved_by=impact_assessment.owner_approved_by,
        owner_approved_at=impact_assessment.owner_approved_at,
        caigo_approved_by=impact_assessment.caigo_approved_by,
        caigo_approved_at=impact_assessment.caigo_approved_at,
        created_at=impact_assessment.created_at,
        updated_at=impact_assessment.updated_at,
        framework_tags=framework_tags,
        factors=[ImpactFactorAssessmentRead.model_validate(f) for f in factors],
    )


@risk_assessments_router.get(
    "/{risk_assessment_id}/impact-assessments", response_model=list[ImpactAssessmentRead]
)
def list_impact_assessments(
    risk_assessment_id: int, db: Session = Depends(get_db)
) -> list[ImpactAssessmentRead]:
    assessments = impact_assessment_service.list_for_risk_assessment(db, risk_assessment_id)
    return [_to_read(db, a) for a in assessments]


# There is deliberately no POST under /risk-assessments/{id}: an AI system has
# exactly one impact assessment, and it must already exist (and be completed)
# before a risk assessment can be created at all. Use POST /impact-assessments.


@router.get("", response_model=list[ImpactAssessmentRead])
def list_impact_assessments_for_ai_system(
    ai_system_row_id: int | None = None, db: Session = Depends(get_db)
) -> list[ImpactAssessmentRead]:
    assessments = (
        impact_assessment_service.list_for_ai_system(db, ai_system_row_id)
        if ai_system_row_id is not None
        else impact_assessment_service.list_all(db)
    )
    return [_to_read(db, a) for a in assessments]


@router.post("", response_model=ImpactAssessmentRead, status_code=201)
def create_impact_assessment_for_ai_system(
    data: ImpactAssessmentForSystemCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    """The primary entry point: an impact assessment is performed against an
    AI system before any risk assessment exists for it."""
    impact_assessment = impact_assessment_service.create_for_ai_system(
        db,
        data.ai_system_row_id,
        ImpactAssessmentCreate(
            assessor_id=data.assessor_id, assessment_date=data.assessment_date
        ),
        actor_id,
    )
    return _to_read(db, impact_assessment)


@router.get("/{impact_assessment_id}", response_model=ImpactAssessmentRead)
def get_impact_assessment(
    impact_assessment_id: int, db: Session = Depends(get_db)
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.get(db, impact_assessment_id)
    return _to_read(db, impact_assessment)


@router.put("/{impact_assessment_id}", response_model=ImpactAssessmentRead)
def update_impact_assessment(
    impact_assessment_id: int,
    data: ImpactAssessmentUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.update(
        db, impact_assessment_id, data, actor_id
    )
    return _to_read(db, impact_assessment)


@router.post(
    "/{impact_assessment_id}/submit-for-owner-approval", response_model=ImpactAssessmentRead
)
def submit_for_owner_approval(
    impact_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.submit_for_owner_approval(
        db, impact_assessment_id, actor_id
    )
    return _to_read(db, impact_assessment)


@router.post(
    "/{impact_assessment_id}/approve-owner-stage", response_model=ImpactAssessmentRead
)
def approve_owner_stage(
    impact_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.approve_owner_stage(
        db, impact_assessment_id, actor_id
    )
    return _to_read(db, impact_assessment)


@router.post(
    "/{impact_assessment_id}/approve-caigo-stage", response_model=ImpactAssessmentRead
)
def approve_caigo_stage(
    impact_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.approve_caigo_stage(
        db, impact_assessment_id, actor_id
    )
    return _to_read(db, impact_assessment)


@router.delete("/{impact_assessment_id}", status_code=204)
def delete_impact_assessment(
    impact_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    impact_assessment_service.delete(db, impact_assessment_id, actor_id)


@router.put(
    "/{impact_assessment_id}/factors/{factor}", response_model=ImpactFactorAssessmentRead
)
def update_factor(
    impact_assessment_id: int,
    factor: str,
    data: ImpactFactorAssessmentUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactFactorAssessmentRead:
    factor_assessment = impact_assessment_service.update_factor(
        db,
        impact_assessment_id,
        factor,
        data.benefits,
        data.harms,
        data.criteria,
        data.score,
        actor_id,
    )
    return ImpactFactorAssessmentRead.model_validate(factor_assessment)
