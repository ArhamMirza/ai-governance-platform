"""Planning of changes to the AI management system -- ISO/IEC 42001 6.3.

Gated only by ordinary edit permission, like Suppliers and Objectives. Where
a change stands (planned, in progress, overdue ...) is computed live
(app.core.change_tracking), never stored; only moving it on is a person's
call.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import change_tracking
from app.core.change_tracking import ChangeStanding
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.models.management_system_change import (
    ChangeAISystem,
    ChangeStatus,
    ManagementSystemChange,
)
from app.repositories import change_repository, sheet_repository
from app.schemas.change import ChangeCreate, ChangeStatusUpdate, ChangeUpdate
from app.services import ai_system_inventory_service, audit_service, framework_service

ENTITY_TYPE = "ManagementSystemChange"


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


def standing(change: ManagementSystemChange, as_of: date | None = None) -> ChangeStanding:
    return change_tracking.standing(
        status=change.status,
        started_on=change.started_on,
        closed_on=change.closed_on,
        planned_date=change.planned_date,
        as_of=_today(as_of),
    )


def links_by_change(db: Session) -> dict[int, list[ChangeAISystem]]:
    """Every change's AI system links in one query, for list views."""
    linked: dict[int, list[ChangeAISystem]] = {}
    for link in change_repository.list_links(db):
        linked.setdefault(link.change_id, []).append(link)
    return linked


def _get_or_raise(db: Session, change_id: int) -> ManagementSystemChange:
    change = change_repository.get(db, change_id)
    if change is None:
        raise NotFoundError("ManagementSystemChange", change_id)
    return change


def _validate(change: ManagementSystemChange) -> None:
    """Checked against the change as it will be saved."""
    if change.planned_date < change.raised_on:
        raise ValidationError("The planned date can't be before the change was raised.")


def _validate_ai_system_rows(db: Session, row_ids: list[int]) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    for row_id in row_ids:
        row = sheet_repository.get_row(db, row_id)
        if row is None or row.sheet_id != inventory_sheet.id:
            raise NotFoundError("AISystemRow", row_id)


def list_changes(db: Session, ai_system_row_id: int | None = None) -> list[ManagementSystemChange]:
    changes = change_repository.list_all(db)
    if ai_system_row_id is None:
        return changes
    linked = {
        link.change_id for link in change_repository.list_links_for_ai_system(db, ai_system_row_id)
    }
    return [change for change in changes if change.id in linked]


def get_change(db: Session, change_id: int) -> ManagementSystemChange:
    return _get_or_raise(db, change_id)


def linked_ai_system_ids(db: Session, change_id: int) -> list[int]:
    return [
        link.ai_system_row_id for link in change_repository.list_links_for_change(db, change_id)
    ]


def create_change(
    db: Session, data: ChangeCreate, actor_id: int | None, today: date | None = None
) -> ManagementSystemChange:
    fields = data.model_dump()
    fields["raised_on"] = fields["raised_on"] or _today(today)
    change = ManagementSystemChange(**fields, status=ChangeStatus.PLANNED)
    _validate(change)
    change = change_repository.create(db, change)
    audit_service.log(db, ENTITY_TYPE, change.id, "created", actor_id, {"title": change.title})
    return change


def update_change(
    db: Session, change_id: int, data: ChangeUpdate, actor_id: int | None
) -> ManagementSystemChange:
    change = _get_or_raise(db, change_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("raised_on", "planned_date"):
        if required in changes and changes[required] is None:
            raise ValidationError(
                "A change needs both the date it was raised and its planned date."
            )
    for field, value in changes.items():
        setattr(change, field, value)
    try:
        _validate(change)
    except ValidationError:
        db.rollback()
        raise
    change = change_repository.save(db, change)
    audit_service.log(db, ENTITY_TYPE, change.id, "updated", actor_id, changes)
    return change


def change_status(
    db: Session,
    change_id: int,
    data: ChangeStatusUpdate,
    actor_id: int | None,
    today: date | None = None,
) -> ManagementSystemChange:
    """Moves a change on: start it, implement it, cancel it, or put a
    closed one back to where it was. Dated, so a standing as of an earlier
    date still sees it as it was."""
    change = _get_or_raise(db, change_id)
    reference = _today(today)
    closed = change.status in change_tracking.CLOSED_STATES

    if data.action == "start":
        if change.status != ChangeStatus.PLANNED:
            raise InvalidStatusTransitionError(
                f"Change {change_id} is {change.status}; only a planned change can be started."
            )
        change.status = ChangeStatus.IN_PROGRESS
        change.started_on = reference
    elif data.action in ("implement", "cancel"):
        if closed:
            raise InvalidStatusTransitionError(f"Change {change_id} is already {change.status}.")
        change.status = (
            ChangeStatus.IMPLEMENTED if data.action == "implement" else ChangeStatus.CANCELLED
        )
        change.closed_on = reference
        change.closure_note = data.note
    else:
        if not closed:
            raise InvalidStatusTransitionError(f"Change {change_id} is still open.")
        change.status = (
            ChangeStatus.IN_PROGRESS if change.started_on is not None else ChangeStatus.PLANNED
        )
        change.closed_on = None
        change.closure_note = None

    change = change_repository.save(db, change)
    audit_service.log(
        db,
        ENTITY_TYPE,
        change.id,
        f"status_{data.action}",
        actor_id,
        {"status": change.status, "note": data.note},
    )
    return change


def set_ai_systems(
    db: Session, change_id: int, ai_system_row_ids: list[int], actor_id: int | None
) -> ManagementSystemChange:
    change = _get_or_raise(db, change_id)
    _validate_ai_system_rows(db, ai_system_row_ids)
    change_repository.replace_links(db, change_id, ai_system_row_ids)
    audit_service.log(
        db,
        ENTITY_TYPE,
        change_id,
        "ai_systems_updated",
        actor_id,
        {"ai_system_row_ids": sorted(set(ai_system_row_ids))},
    )
    return change


def delete_change(db: Session, change_id: int, actor_id: int | None) -> None:
    """Only while nothing has happened to it -- once work has started or it's
    been closed, it's part of the record of how the management system
    changed, so it's cancelled instead."""
    from app.services import evidence_service, improvement_service

    change = _get_or_raise(db, change_id)
    # Starting or closing a change always moves it off `planned`, so the
    # status alone says whether anything has happened to it.
    if change.status != ChangeStatus.PLANNED:
        raise InvalidStatusTransitionError(
            "This change has been started or closed, so it can't be deleted; cancel it instead."
        )
    change_repository.delete_links(db, change_repository.list_links_for_change(db, change_id))
    improvement_service.unlink_change(db, change_id, actor_id)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, change_id)
    framework_service.delete_tags(db, ENTITY_TYPE, change_id)
    change_repository.delete(db, change)
    audit_service.log(db, ENTITY_TYPE, change_id, "deleted", actor_id, {"title": change.title})


def unlink_ai_system(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    """Drops every change's link to an AI system being deleted. The changes
    themselves survive -- they're changes to the management system, not to
    any one AI system."""
    links = change_repository.list_links_for_ai_system(db, ai_system_row_id)
    if not links:
        return
    change_repository.delete_links(db, links)
    for link in links:
        audit_service.log(
            db,
            ENTITY_TYPE,
            link.change_id,
            "ai_system_unlinked",
            actor_id,
            {"ai_system_row_id": ai_system_row_id},
        )


def standings_as_of(
    db: Session, as_of: date
) -> list[tuple[ManagementSystemChange, ChangeStanding]]:
    """Every change that had been raised by `as_of`, with where it stood
    then -- what a management review meeting on that date was looking at."""
    return [
        (change, standing(change, as_of))
        for change in change_repository.list_all(db)
        if change_tracking.exists_as_of(change.raised_on, as_of)
    ]


def overdue_count(db: Session, today: date | None = None) -> int:
    """Open changes past their planned date -- for the dashboard."""
    return sum(1 for change in change_repository.list_all(db) if standing(change, today).overdue)
