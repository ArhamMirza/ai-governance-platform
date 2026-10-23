from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_settings_actor_id
from app.schemas.ai_assist import (
    AiAssistSettingsRead,
    AiAssistSettingsUpdate,
    AiAssistStatus,
    AiSpendReport,
    DraftRequest,
    DraftResponse,
)
from app.services import ai_assist_service, ai_spend_service

router = APIRouter(prefix="/ai-assist", tags=["ai-assist"])


@router.get("/status", response_model=AiAssistStatus)
def get_status(db: Session = Depends(get_db)) -> AiAssistStatus:
    """Whether AI assistance is configured, for any signed-in user.

    Readable by everyone because the UI has to decide whether to offer the
    feature at all -- it carries no credential, only the provider and model
    names, which the same people can see on every drafted record anyway.
    """
    return ai_assist_service.status(db)


@router.get("/settings", response_model=AiAssistSettingsRead)
def get_ai_settings(
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_settings_actor_id),
) -> AiAssistSettingsRead:
    return ai_assist_service.get_settings(db)


@router.put("/settings", response_model=AiAssistSettingsRead)
def update_ai_settings(
    data: AiAssistSettingsUpdate,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_settings_actor_id),
) -> AiAssistSettingsRead:
    return ai_assist_service.update_settings(db, data, actor_id)


@router.get("/spend", response_model=AiSpendReport)
def spend(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_settings_actor_id),
) -> AiSpendReport:
    """Where this deployment's AI tokens go, by kind of call and by day. Admins
    only: it is part of how the AI is configured and paid for."""
    return ai_spend_service.report(db, days)


@router.post("/draft", response_model=DraftResponse)
def draft(
    data: DraftRequest,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> DraftResponse:
    """Draft one field. Gated on EDIT -- the same bar as typing it by hand,
    since that is exactly what this produces: text in a box, saved only if
    the person who asked for it decides to keep it."""
    return ai_assist_service.draft_field(
        db,
        kind=data.kind,
        impact_assessment_id=data.impact_assessment_id,
        factor=data.factor,
        actor_id=actor_id,
    )
