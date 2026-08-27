from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.framework_control import FrameworkControlRead
from app.services import framework_service

router = APIRouter(prefix="/framework-controls", tags=["framework-controls"])


@router.get("", response_model=list[FrameworkControlRead])
def list_controls(
    framework: str | None = None, db: Session = Depends(get_db)
) -> list[FrameworkControlRead]:
    return framework_service.list_controls(db, framework)
