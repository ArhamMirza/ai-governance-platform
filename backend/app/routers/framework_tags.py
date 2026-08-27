from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.framework_control import FrameworkControlRead, FrameworkTagsUpdate
from app.services import framework_service

router = APIRouter(prefix="/framework-tags", tags=["framework-tags"])


@router.get("", response_model=list[FrameworkControlRead])
def get_tags(
    entity_type: str, entity_id: int, db: Session = Depends(get_db)
) -> list[FrameworkControlRead]:
    return framework_service.get_tags(db, entity_type, entity_id)


@router.put("", response_model=list[FrameworkControlRead])
def set_tags(
    entity_type: str,
    entity_id: int,
    data: FrameworkTagsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> list[FrameworkControlRead]:
    return framework_service.set_tags(db, entity_type, entity_id, data.control_ids, actor_id)
