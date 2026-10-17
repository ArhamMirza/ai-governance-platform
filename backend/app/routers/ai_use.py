"""Settings, the enrollment key and the usage counts for the organization's
AI-use controls. Administrators only: the counts say who used what."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_settings_actor_id, require_manage_settings_user
from app.models.ai_dlp import AIUseSettings
from app.schemas.ai_use import (
    AIUseSettingsRead,
    AIUseSettingsUpdate,
    EnrollmentKeyIssued,
    UsageSummary,
)
from app.services import ai_usage_service, framework_service

router = APIRouter(
    prefix="/ai-use", tags=["ai-use"], dependencies=[Depends(require_manage_settings_user)]
)


def _to_read(db: Session, settings: AIUseSettings) -> AIUseSettingsRead:
    return AIUseSettingsRead(
        id=settings.id,
        unapproved_site_action=settings.unapproved_site_action,
        retention_days=settings.retention_days,
        staff_notice=settings.staff_notice,
        enrollment_key_issued=settings.enrollment_key_hash is not None,
        enrollment_key_hint=settings.enrollment_key_hint,
        enrollment_key_created_on=settings.enrollment_key_created_on,
        framework_tags=framework_service.get_tags(db, ai_usage_service.ENTITY_TYPE, settings.id),
    )


@router.get("/settings", response_model=AIUseSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> AIUseSettingsRead:
    return _to_read(db, ai_usage_service.get_settings(db))


@router.put("/settings", response_model=AIUseSettingsRead)
def update_settings(
    data: AIUseSettingsUpdate,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_settings_actor_id),
) -> AIUseSettingsRead:
    return _to_read(db, ai_usage_service.update_settings(db, data, actor_id))


@router.post("/enrollment-key", response_model=EnrollmentKeyIssued, status_code=201)
def rotate_enrollment_key(
    db: Session = Depends(get_db), actor_id: int = Depends(get_current_settings_actor_id)
) -> EnrollmentKeyIssued:
    """Issues a new key and revokes the old one. The key is in this response
    and nowhere else."""
    key, hint = ai_usage_service.rotate_enrollment_key(db, actor_id)
    return EnrollmentKeyIssued(key=key, hint=hint)


@router.get("/usage", response_model=UsageSummary)
def usage(
    days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)
) -> UsageSummary:
    return ai_usage_service.usage_summary(db, days)
