from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.risk_criteria import RiskCriteriaRead, RiskCriteriaUpdate
from app.services import risk_criteria_service

router = APIRouter(prefix="/risk-criteria", tags=["risk-criteria"])


@router.get("", response_model=RiskCriteriaRead)
def get_criteria(db: Session = Depends(get_db)) -> RiskCriteriaRead:
    return risk_criteria_service.get_criteria(db)


@router.put("", response_model=RiskCriteriaRead)
def update_criteria(
    data: RiskCriteriaUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskCriteriaRead:
    return risk_criteria_service.update_criteria(db, data, actor_id)


@router.post("/reset", response_model=RiskCriteriaRead)
def reset_criteria(
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskCriteriaRead:
    return risk_criteria_service.reset_criteria(db, actor_id)
