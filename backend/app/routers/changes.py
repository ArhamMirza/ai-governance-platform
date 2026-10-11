from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.change_tracking import ChangeStanding
from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.management_system_change import ManagementSystemChange
from app.schemas.change import (
    ChangeAISystemsUpdate,
    ChangeAsOfRead,
    ChangeCreate,
    ChangeRead,
    ChangeStandingRead,
    ChangeStatusUpdate,
    ChangeUpdate,
)
from app.services import change_service, framework_service

router = APIRouter(prefix="/changes", tags=["changes"])


def _standing_read(standing: ChangeStanding) -> ChangeStandingRead:
    return ChangeStandingRead(state=standing.state, overdue=standing.overdue)


def _to_read(
    db: Session, change: ManagementSystemChange, ai_system_row_ids: list[int]
) -> ChangeRead:
    return ChangeRead(
        id=change.id,
        title=change.title,
        description=change.description,
        change_type=change.change_type,
        reason=change.reason,
        consequences=change.consequences,
        resources_needed=change.resources_needed,
        owner_id=change.owner_id,
        raised_on=change.raised_on,
        planned_date=change.planned_date,
        status=change.status,
        started_on=change.started_on,
        closed_on=change.closed_on,
        closure_note=change.closure_note,
        ai_system_row_ids=ai_system_row_ids,
        standing=_standing_read(change_service.standing(change)),
        framework_tags=framework_service.get_tags(db, change_service.ENTITY_TYPE, change.id),
        created_at=change.created_at,
        updated_at=change.updated_at,
    )


def _detail(db: Session, change: ManagementSystemChange) -> ChangeRead:
    return _to_read(db, change, change_service.linked_ai_system_ids(db, change.id))


@router.get("", response_model=list[ChangeRead])
def list_changes(
    ai_system_row_id: int | None = None, db: Session = Depends(get_db)
) -> list[ChangeRead]:
    links = change_service.links_by_change(db)
    return [
        _to_read(db, change, [link.ai_system_row_id for link in links.get(change.id, [])])
        for change in change_service.list_changes(db, ai_system_row_id)
    ]


@router.post("", response_model=ChangeRead, status_code=201)
def create_change(
    data: ChangeCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ChangeRead:
    return _detail(db, change_service.create_change(db, data, actor_id))


# Declared before the /{change_id} routes, so "standing" isn't taken for an id.
@router.get("/standing", response_model=list[ChangeAsOfRead])
def standing_as_of(as_of: date, db: Session = Depends(get_db)) -> list[ChangeAsOfRead]:
    return [
        ChangeAsOfRead(
            id=change.id,
            title=change.title,
            change_type=change.change_type,
            owner_id=change.owner_id,
            planned_date=change.planned_date,
            standing=_standing_read(standing),
        )
        for change, standing in change_service.standings_as_of(db, as_of)
    ]


@router.get("/{change_id}", response_model=ChangeRead)
def get_change(change_id: int, db: Session = Depends(get_db)) -> ChangeRead:
    return _detail(db, change_service.get_change(db, change_id))


@router.put("/{change_id}", response_model=ChangeRead)
def update_change(
    change_id: int,
    data: ChangeUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ChangeRead:
    return _detail(db, change_service.update_change(db, change_id, data, actor_id))


@router.delete("/{change_id}", status_code=204)
def delete_change(
    change_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    change_service.delete_change(db, change_id, actor_id)


@router.post("/{change_id}/status", response_model=ChangeRead)
def change_status(
    change_id: int,
    data: ChangeStatusUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ChangeRead:
    return _detail(db, change_service.change_status(db, change_id, data, actor_id))


@router.put("/{change_id}/ai-systems", response_model=ChangeRead)
def set_ai_systems(
    change_id: int,
    data: ChangeAISystemsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ChangeRead:
    change = change_service.set_ai_systems(db, change_id, data.ai_system_row_ids, actor_id)
    return _detail(db, change)
