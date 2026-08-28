from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.framework_control import FrameworkMappingEntry
from app.services import framework_service

router = APIRouter(prefix="/framework-mapping", tags=["framework-mapping"])


@router.get("", response_model=list[FrameworkMappingEntry])
def get_mapping(
    framework: str | None = None, db: Session = Depends(get_db)
) -> list[FrameworkMappingEntry]:
    return framework_service.get_mapping(db, framework)
