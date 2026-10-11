"""Communication plan -- ISO/IEC 42001 7.4: what the organization
communicates about the AI management system, with whom, how, and when.

Gated only by ordinary edit permission, like Suppliers and Objectives. When a
communication is next due is computed live (app.core.communication_schedule)
from the records of it having been done, never stored.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import communication_schedule
from app.core.exceptions import NotFoundError, ValidationError
from app.models.communication import (
    CommunicationPlanItem,
    CommunicationRecord,
    CommunicationStatus,
)
from app.repositories import communication_repository
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationRecordCreate,
    CommunicationUpdate,
)
from app.services import audit_service, framework_service

ENTITY_TYPE = "CommunicationPlanItem"
RECORD_ENTITY_TYPE = "CommunicationRecord"


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


@dataclass(frozen=True)
class Standing:
    last_communicated_on: date | None
    next_due: date | None
    overdue: bool


def standing(
    item: CommunicationPlanItem, communicated_dates: list[date], today: date | None = None
) -> Standing:
    due = communication_schedule.next_due(item.interval_months, item.first_due, communicated_dates)
    return Standing(
        last_communicated_on=max(communicated_dates) if communicated_dates else None,
        next_due=due,
        overdue=communication_schedule.is_overdue(
            item.status == CommunicationStatus.ACTIVE, due, _today(today)
        ),
    )


def dates_by_item(db: Session) -> dict[int, list[date]]:
    """Every item's communicated dates in one query, for list views and the
    dashboard rather than one query per item."""
    dates: dict[int, list[date]] = defaultdict(list)
    for record in communication_repository.list_records(db):
        dates[record.communication_id].append(record.communicated_on)
    return dates


def _get_or_raise(db: Session, item_id: int) -> CommunicationPlanItem:
    item = communication_repository.get(db, item_id)
    if item is None:
        raise NotFoundError("CommunicationPlanItem", item_id)
    return item


def _validate(item: CommunicationPlanItem) -> None:
    """Checked against the item as it will be saved, so no partial update
    can leave it half-scheduled."""
    if (item.interval_months is None) != (item.first_due is None):
        raise ValidationError(
            "Set both how often this is communicated and when it's first due, or neither "
            "(for something done only when it's needed)."
        )


def list_items(db: Session) -> list[CommunicationPlanItem]:
    return communication_repository.list_all(db)


def get_item(db: Session, item_id: int) -> CommunicationPlanItem:
    return _get_or_raise(db, item_id)


def list_records(db: Session, item_id: int) -> list[CommunicationRecord]:
    return communication_repository.list_records_for_item(db, item_id)


def create_item(
    db: Session, data: CommunicationCreate, actor_id: int | None
) -> CommunicationPlanItem:
    item = CommunicationPlanItem(**data.model_dump(), status=CommunicationStatus.ACTIVE)
    _validate(item)
    item = communication_repository.create(db, item)
    audit_service.log(db, ENTITY_TYPE, item.id, "created", actor_id, {"topic": item.topic})
    return item


def update_item(
    db: Session, item_id: int, data: CommunicationUpdate, actor_id: int | None
) -> CommunicationPlanItem:
    item = _get_or_raise(db, item_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("topic", "audience"):
        if required in changes and not changes[required]:
            raise ValidationError("A planned communication needs a topic and an audience.")
    for field, value in changes.items():
        setattr(item, field, value)
    try:
        _validate(item)
    except ValidationError:
        db.rollback()
        raise
    item = communication_repository.save(db, item)
    audit_service.log(db, ENTITY_TYPE, item.id, "updated", actor_id, changes)
    return item


def record_communication(
    db: Session,
    item_id: int,
    data: CommunicationRecordCreate,
    actor_id: int | None,
    today: date | None = None,
) -> CommunicationRecord:
    _get_or_raise(db, item_id)
    if data.communicated_on > _today(today):
        raise ValidationError("A communication can't be dated in the future.")
    record = communication_repository.create_record(
        db,
        CommunicationRecord(
            communication_id=item_id,
            communicated_on=data.communicated_on,
            summary=data.summary,
            recorded_by=actor_id,
        ),
    )
    audit_service.log(
        db,
        ENTITY_TYPE,
        item_id,
        "communication_recorded",
        actor_id,
        {"record_id": record.id, "communicated_on": record.communicated_on},
    )
    return record


def delete_record(db: Session, record_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope, matching supplier_service:
    # evidence_service imports services back.
    from app.services import evidence_service

    record = communication_repository.get_record(db, record_id)
    if record is None:
        raise NotFoundError("CommunicationRecord", record_id)
    item_id = record.communication_id
    evidence_service.delete_all_for_entity(db, RECORD_ENTITY_TYPE, record_id)
    communication_repository.delete_record(db, record)
    audit_service.log(
        db, ENTITY_TYPE, item_id, "record_deleted", actor_id, {"record_id": record_id}
    )


def delete_item(db: Session, item_id: int, actor_id: int | None) -> None:
    from app.services import evidence_service

    item = _get_or_raise(db, item_id)
    for record in communication_repository.list_records_for_item(db, item_id):
        evidence_service.delete_all_for_entity(db, RECORD_ENTITY_TYPE, record.id)
        communication_repository.delete_record(db, record)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, item_id)
    framework_service.delete_tags(db, ENTITY_TYPE, item_id)
    communication_repository.delete(db, item)
    audit_service.log(db, ENTITY_TYPE, item_id, "deleted", actor_id, {"topic": item.topic})


def overdue_count(db: Session, today: date | None = None) -> int:
    """Active communications past their due date -- for the dashboard."""
    dates = dates_by_item(db)
    return sum(
        1
        for item in communication_repository.list_all(db)
        if standing(item, dates[item.id], today).overdue
    )
