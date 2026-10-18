from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_manage_settings_user
from app.models.user import User
from app.schemas.mfa import SecuritySettingsRead, SecuritySettingsUpdate
from app.services import mfa_service

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/settings", response_model=SecuritySettingsRead)
def get_settings(
    db: Session = Depends(get_db), _: User = Depends(require_manage_settings_user)
) -> SecuritySettingsRead:
    return mfa_service.read_settings(db)


@router.put("/settings", response_model=SecuritySettingsRead)
def update_settings(
    data: SecuritySettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_settings_user),
) -> SecuritySettingsRead:
    """Whether administrators must use two-step sign-in. It can only be turned
    on by an administrator who has it on themselves."""
    return mfa_service.update_settings(db, data.require_mfa_for_admins, actor)
