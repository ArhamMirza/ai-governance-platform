from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.eu_ai_act import (
    EuAiActApplicabilityRead,
    EuAiActApplicabilityUpdate,
    EuAiActArticleOverrideUpdate,
    EuAiActArticleRead,
)
from app.services import eu_ai_act_service

router = APIRouter(prefix="/eu-ai-act", tags=["eu-ai-act"])


@router.get("/applicability", response_model=EuAiActApplicabilityRead)
def get_applicability(db: Session = Depends(get_db)) -> EuAiActApplicabilityRead:
    return eu_ai_act_service.read_settings(db)


@router.put("/applicability", response_model=EuAiActApplicabilityRead)
def update_applicability(
    data: EuAiActApplicabilityUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> EuAiActApplicabilityRead:
    return eu_ai_act_service.update_settings(db, data, actor_id)


@router.get("/articles", response_model=list[EuAiActArticleRead])
def list_articles(db: Session = Depends(get_db)) -> list[EuAiActArticleRead]:
    return eu_ai_act_service.article_statuses(db)


@router.put("/articles/{control_id}/override", response_model=list[EuAiActArticleRead])
def set_override(
    control_id: int,
    data: EuAiActArticleOverrideUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> list[EuAiActArticleRead]:
    eu_ai_act_service.set_override(db, control_id, data.applicability, data.justification, actor_id)
    return eu_ai_act_service.article_statuses(db)


@router.delete("/articles/{control_id}/override", response_model=list[EuAiActArticleRead])
def clear_override(
    control_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> list[EuAiActArticleRead]:
    eu_ai_act_service.clear_override(db, control_id, actor_id)
    return eu_ai_act_service.article_statuses(db)
