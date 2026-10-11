from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.communication import CommunicationPlanItem
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationDetailRead,
    CommunicationRead,
    CommunicationRecordCreate,
    CommunicationRecordRead,
    CommunicationUpdate,
)
from app.services import communication_service, framework_service

router = APIRouter(prefix="/communications", tags=["communications"])


def _to_read(
    db: Session, item: CommunicationPlanItem, communicated_dates: list[date]
) -> CommunicationRead:
    standing = communication_service.standing(item, communicated_dates)
    return CommunicationRead(
        id=item.id,
        topic=item.topic,
        audience=item.audience,
        direction=item.direction,
        method=item.method,
        responsible_id=item.responsible_id,
        notes=item.notes,
        status=item.status,
        interval_months=item.interval_months,
        first_due=item.first_due,
        last_communicated_on=standing.last_communicated_on,
        next_due=standing.next_due,
        overdue=standing.overdue,
        framework_tags=framework_service.get_tags(db, communication_service.ENTITY_TYPE, item.id),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_detail(db: Session, item: CommunicationPlanItem) -> CommunicationDetailRead:
    records = communication_service.list_records(db, item.id)
    base = _to_read(db, item, [record.communicated_on for record in records])
    return CommunicationDetailRead(
        **base.model_dump(),
        records=[CommunicationRecordRead.model_validate(record) for record in records],
    )


@router.get("", response_model=list[CommunicationRead])
def list_communications(db: Session = Depends(get_db)) -> list[CommunicationRead]:
    dates = communication_service.dates_by_item(db)
    return [_to_read(db, item, dates[item.id]) for item in communication_service.list_items(db)]


@router.post("", response_model=CommunicationDetailRead, status_code=201)
def create_communication(
    data: CommunicationCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CommunicationDetailRead:
    return _to_detail(db, communication_service.create_item(db, data, actor_id))


# Declared before the /{item_id} routes: otherwise DELETE /records/5 matches
# DELETE /{item_id} first and fails its int validation.
@router.delete("/records/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    communication_service.delete_record(db, record_id, actor_id)


@router.get("/{item_id}", response_model=CommunicationDetailRead)
def get_communication(item_id: int, db: Session = Depends(get_db)) -> CommunicationDetailRead:
    return _to_detail(db, communication_service.get_item(db, item_id))


@router.put("/{item_id}", response_model=CommunicationDetailRead)
def update_communication(
    item_id: int,
    data: CommunicationUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CommunicationDetailRead:
    return _to_detail(db, communication_service.update_item(db, item_id, data, actor_id))


@router.delete("/{item_id}", status_code=204)
def delete_communication(
    item_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    communication_service.delete_item(db, item_id, actor_id)


@router.post("/{item_id}/records", response_model=CommunicationRecordRead, status_code=201)
def record_communication(
    item_id: int,
    data: CommunicationRecordCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CommunicationRecordRead:
    record = communication_service.record_communication(db, item_id, data, actor_id)
    return CommunicationRecordRead.model_validate(record)
