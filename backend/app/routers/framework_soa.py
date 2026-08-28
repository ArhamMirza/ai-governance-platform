from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.framework_control import FrameworkSoaEntryRead, FrameworkSoaEntryUpdate
from app.services import framework_service

router = APIRouter(prefix="/framework-soa", tags=["framework-soa"])


@router.get("", response_model=list[FrameworkSoaEntryRead])
def get_soa(db: Session = Depends(get_db)) -> list[FrameworkSoaEntryRead]:
    return framework_service.get_soa(db)


@router.put("/{control_id}", response_model=FrameworkSoaEntryRead)
def update_soa_entry(
    control_id: int,
    data: FrameworkSoaEntryUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> FrameworkSoaEntryRead:
    return framework_service.update_soa_entry(
        db, control_id, data.applicability, data.justification, actor_id
    )
