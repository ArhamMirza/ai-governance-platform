from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.impact_assessment import ImpactAssessment
from app.schemas.impact_assessment import (
    ImpactAssessmentCreate,
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
        system_description=impact_assessment.system_description,
        intended_purpose=impact_assessment.intended_purpose,
        foreseeable_misuse=impact_assessment.foreseeable_misuse,
        data_and_model_info=impact_assessment.data_and_model_info,
        deployment_environment=impact_assessment.deployment_environment,
        affected_interested_parties=impact_assessment.affected_interested_parties,
        human_oversight_role=impact_assessment.human_oversight_role,
        conclusion=impact_assessment.conclusion,
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


@risk_assessments_router.post(
    "/{risk_assessment_id}/impact-assessments",
    response_model=ImpactAssessmentRead,
    status_code=201,
)
def create_impact_assessment(
    risk_assessment_id: int,
    data: ImpactAssessmentCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    impact_assessment = impact_assessment_service.create_for_risk_assessment(
        db, risk_assessment_id, data, actor_id
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
