from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import communication_repository
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationRecordCreate,
    CommunicationUpdate,
)
from app.services import communication_service, framework_service

TODAY = date(2026, 6, 15)


def make_item(db: Session, **overrides):
    data = {
        "topic": "Quarterly AI governance update",
        "audience": "Leadership team",
        "direction": "internal",
        "interval_months": 3,
        "first_due": date(2026, 3, 31),
    }
    data.update(overrides)
    return communication_service.create_item(db, CommunicationCreate(**data), actor_id=None)


def record(db: Session, item_id: int, communicated_on: date, summary: str | None = None):
    return communication_service.record_communication(
        db,
        item_id,
        CommunicationRecordCreate(communicated_on=communicated_on, summary=summary),
        actor_id=None,
        today=TODAY,
    )


def dates_of(db: Session, item_id: int) -> list[date]:
    return [r.communicated_on for r in communication_service.list_records(db, item_id)]


def test_a_new_item_is_active_and_nothing_has_been_done(db_session: Session) -> None:
    item = make_item(db_session)

    standing = communication_service.standing(item, [], TODAY)

    assert item.status == "active"
    assert (standing.last_communicated_on, standing.next_due, standing.overdue) == (
        None,
        date(2026, 3, 31),
        True,
    )


def test_an_item_with_no_schedule_is_event_driven(db_session: Session) -> None:
    item = make_item(
        db_session,
        topic="Notify customers of an incident",
        audience="Affected customers",
        direction="external",
        interval_months=None,
        first_due=None,
    )

    standing = communication_service.standing(item, [], TODAY)

    assert (standing.next_due, standing.overdue) == (None, False)


@pytest.mark.parametrize(
    "overrides", [{"interval_months": 3, "first_due": None}, {"interval_months": None}]
)
def test_half_a_schedule_is_refused(db_session: Session, overrides) -> None:
    with pytest.raises(ValidationError):
        make_item(db_session, **overrides)


def test_a_failed_update_leaves_the_item_unchanged(db_session: Session) -> None:
    item = make_item(db_session)

    with pytest.raises(ValidationError):
        communication_service.update_item(
            db_session, item.id, CommunicationUpdate(first_due=None), actor_id=None
        )
    with pytest.raises(ValidationError):
        communication_service.update_item(
            db_session, item.id, CommunicationUpdate(topic=None), actor_id=None
        )

    assert communication_service.get_item(db_session, item.id).first_due == date(2026, 3, 31)


def test_recording_a_communication_moves_the_next_due_date_on(db_session: Session) -> None:
    item = make_item(db_session)
    record(db_session, item.id, date(2026, 6, 1), "Presented to the board")

    standing = communication_service.standing(item, dates_of(db_session, item.id), TODAY)

    assert standing.last_communicated_on == date(2026, 6, 1)
    assert (standing.next_due, standing.overdue) == (date(2026, 9, 1), False)


def test_a_communication_cant_be_dated_in_the_future(db_session: Session) -> None:
    item = make_item(db_session)

    with pytest.raises(ValidationError):
        record(db_session, item.id, date(2026, 6, 16))


def test_a_retired_item_is_never_overdue(db_session: Session) -> None:
    item = make_item(db_session)
    communication_service.update_item(
        db_session, item.id, CommunicationUpdate(status="retired"), actor_id=None
    )

    standing = communication_service.standing(
        communication_service.get_item(db_session, item.id), [], TODAY
    )

    assert standing.overdue is False


def test_deleting_a_record_reopens_the_gap(db_session: Session) -> None:
    item = make_item(db_session)
    made = record(db_session, item.id, date(2026, 6, 1))
    assert (
        communication_service.standing(item, dates_of(db_session, item.id), TODAY).overdue is False
    )

    communication_service.delete_record(db_session, made.id, actor_id=None)

    assert (
        communication_service.standing(item, dates_of(db_session, item.id), TODAY).overdue is True
    )


def test_deleting_an_unknown_record_is_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        communication_service.delete_record(db_session, 999, actor_id=None)


def test_deleting_an_item_removes_its_records_and_tags(db_session: Session) -> None:
    item = make_item(db_session)
    record(db_session, item.id, date(2026, 6, 1))

    communication_service.delete_item(db_session, item.id, actor_id=None)

    assert communication_repository.list_records_for_item(db_session, item.id) == []
    assert framework_service.get_tags(db_session, "CommunicationPlanItem", item.id) == []
    with pytest.raises(NotFoundError):
        communication_service.get_item(db_session, item.id)


def test_the_overdue_count_covers_only_active_items_past_due(db_session: Session) -> None:
    make_item(db_session, topic="Never done")  # First due 2026-03-31 -- overdue.
    done = make_item(db_session, topic="Done recently")
    record(db_session, done.id, date(2026, 6, 1))
    make_item(db_session, topic="Only when needed", interval_months=None, first_due=None)
    stopped = make_item(db_session, topic="Stopped")
    communication_service.update_item(
        db_session, stopped.id, CommunicationUpdate(status="retired"), actor_id=None
    )

    assert communication_service.overdue_count(db_session, TODAY) == 1
