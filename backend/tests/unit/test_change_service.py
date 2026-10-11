from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.repositories import change_repository
from app.schemas.change import ChangeCreate, ChangeStatusUpdate, ChangeUpdate
from app.services import ai_system_inventory_service, change_service, framework_service

TODAY = date(2026, 6, 15)


def make_ai_system(db: Session, name: str = "Resume Screener") -> int:
    return ai_system_inventory_service.add_row(db, {"name": name}, actor_id=None).id


def make_change(db: Session, **overrides):
    data = {
        "title": "Move the screener to a new base model",
        "change_type": "ai_system",
        "raised_on": date(2026, 6, 1),
        "planned_date": date(2026, 7, 31),
    }
    data.update(overrides)
    return change_service.create_change(db, ChangeCreate(**data), actor_id=None)


def move(db: Session, change_id: int, action: str, note: str | None = None, today=TODAY):
    return change_service.change_status(
        db, change_id, ChangeStatusUpdate(action=action, note=note), actor_id=None, today=today
    )


def test_raised_on_defaults_to_today_and_it_starts_planned(db_session: Session) -> None:
    change = change_service.create_change(
        db_session,
        ChangeCreate(title="Update the AI policy", planned_date=date(2026, 9, 1)),
        actor_id=None,
        today=TODAY,
    )

    assert (change.raised_on, change.status, change.started_on) == (TODAY, "planned", None)


def test_the_planned_date_cant_be_before_it_was_raised(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        make_change(db_session, planned_date=date(2026, 5, 31))


def test_a_failed_update_leaves_the_change_unchanged(db_session: Session) -> None:
    change = make_change(db_session)

    with pytest.raises(ValidationError):
        change_service.update_change(
            db_session, change.id, ChangeUpdate(planned_date=date(2026, 1, 1)), actor_id=None
        )
    with pytest.raises(ValidationError):
        change_service.update_change(
            db_session, change.id, ChangeUpdate(planned_date=None), actor_id=None
        )

    assert change_service.get_change(db_session, change.id).planned_date == date(2026, 7, 31)


def test_moving_a_change_through_its_life_is_dated(db_session: Session) -> None:
    change = make_change(db_session)

    started = move(db_session, change.id, "start", today=date(2026, 6, 10))
    assert (started.status, started.started_on) == ("in_progress", date(2026, 6, 10))

    done = move(db_session, change.id, "implement", "Rolled out", today=date(2026, 7, 20))
    assert (done.status, done.closed_on, done.closure_note) == (
        "implemented",
        date(2026, 7, 20),
        "Rolled out",
    )


def test_a_change_can_be_implemented_or_cancelled_without_being_started(
    db_session: Session,
) -> None:
    first = make_change(db_session)
    second = make_change(db_session, title="Drop the vendor")

    assert move(db_session, first.id, "implement").status == "implemented"
    assert move(db_session, second.id, "cancel", "No longer needed").status == "cancelled"


@pytest.mark.parametrize(
    ("setup", "action"),
    [
        (["start"], "start"),  # Already started.
        (["implement"], "start"),  # Closed changes aren't started.
        (["implement"], "cancel"),  # Closed changes aren't closed again.
        (["cancel"], "implement"),
        ([], "reopen"),  # Nothing to reopen.
        (["start"], "reopen"),
    ],
)
def test_impossible_moves_are_refused(db_session: Session, setup, action) -> None:
    change = make_change(db_session)
    for step in setup:
        move(db_session, change.id, step)

    with pytest.raises(InvalidStatusTransitionError):
        move(db_session, change.id, action)


def test_reopening_goes_back_to_where_it_was(db_session: Session) -> None:
    started = make_change(db_session, title="Started before closing")
    move(db_session, started.id, "start", today=date(2026, 6, 5))
    move(db_session, started.id, "cancel", "Paused")
    never_started = make_change(db_session, title="Never started")
    move(db_session, never_started.id, "cancel")

    reopened = move(db_session, started.id, "reopen")
    other = move(db_session, never_started.id, "reopen")

    assert (reopened.status, reopened.closed_on, reopened.closure_note) == (
        "in_progress",
        None,
        None,
    )
    assert reopened.started_on == date(2026, 6, 5)
    assert (other.status, other.started_on) == ("planned", None)


def test_only_an_untouched_change_can_be_deleted(db_session: Session) -> None:
    started = make_change(db_session, title="Started")
    move(db_session, started.id, "start")
    cancelled = make_change(db_session, title="Cancelled")
    move(db_session, cancelled.id, "cancel")
    untouched = make_change(db_session, title="Untouched")

    for change in (started, cancelled):
        with pytest.raises(InvalidStatusTransitionError):
            change_service.delete_change(db_session, change.id, actor_id=None)

    change_service.delete_change(db_session, untouched.id, actor_id=None)
    with pytest.raises(NotFoundError):
        change_service.get_change(db_session, untouched.id)


def test_deleting_a_change_removes_its_links_and_tags(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    change = make_change(db_session)
    change_service.set_ai_systems(db_session, change.id, [row_id], actor_id=None)

    change_service.delete_change(db_session, change.id, actor_id=None)

    assert change_repository.list_links_for_ai_system(db_session, row_id) == []
    assert framework_service.get_tags(db_session, "ManagementSystemChange", change.id) == []


def test_relinking_keeps_surviving_links(db_session: Session) -> None:
    first, second, third = (make_ai_system(db_session, name) for name in ("A", "B", "C"))
    change = make_change(db_session)
    change_service.set_ai_systems(db_session, change.id, [first, second], actor_id=None)
    kept = {
        link.ai_system_row_id: link.id
        for link in change_repository.list_links_for_change(db_session, change.id)
    }

    change_service.set_ai_systems(db_session, change.id, [second, third], actor_id=None)

    links = change_repository.list_links_for_change(db_session, change.id)
    assert [link.ai_system_row_id for link in links] == [second, third]
    assert next(link.id for link in links if link.ai_system_row_id == second) == kept[second]


def test_linking_an_unknown_ai_system_is_refused(db_session: Session) -> None:
    change = make_change(db_session)

    with pytest.raises(NotFoundError):
        change_service.set_ai_systems(db_session, change.id, [999], actor_id=None)


def test_filtering_by_ai_system(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    linked = make_change(db_session, title="Linked")
    make_change(db_session, title="Not linked")
    change_service.set_ai_systems(db_session, linked.id, [row_id], actor_id=None)

    assert [c.title for c in change_service.list_changes(db_session, row_id)] == ["Linked"]


def test_deleting_an_ai_system_unlinks_it_without_deleting_the_change(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    change = make_change(db_session)
    change_service.set_ai_systems(db_session, change.id, [row_id], actor_id=None)

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    assert change_service.get_change(db_session, change.id).title
    assert change_service.linked_ai_system_ids(db_session, change.id) == []


def test_standings_as_of_skip_changes_raised_later_and_see_what_was_known(
    db_session: Session,
) -> None:
    early = make_change(db_session, title="Early", planned_date=date(2026, 7, 1))
    move(db_session, early.id, "start", today=date(2026, 6, 10))
    move(db_session, early.id, "implement", today=date(2026, 7, 20))
    make_change(
        db_session, title="Later", raised_on=date(2026, 7, 5), planned_date=date(2026, 9, 1)
    )

    in_june = change_service.standings_as_of(db_session, date(2026, 6, 20))
    in_july = change_service.standings_as_of(db_session, date(2026, 7, 15))
    in_august = change_service.standings_as_of(db_session, date(2026, 8, 1))

    assert [(c.title, s.state, s.overdue) for c, s in in_june] == [("Early", "in_progress", False)]
    # Past its planned date and not yet implemented, so late that day ...
    assert [(c.title, s.state, s.overdue) for c, s in in_july] == [
        ("Early", "in_progress", True),
        ("Later", "planned", False),
    ]
    # ... and no longer once it was.
    assert {c.title: (s.state, s.overdue) for c, s in in_august} == {
        "Early": ("implemented", False),
        "Later": ("planned", False),
    }


def test_the_overdue_count_covers_only_open_changes_past_their_date(db_session: Session) -> None:
    make_change(db_session, title="Late", planned_date=date(2026, 6, 10))
    started = make_change(db_session, title="Late and started", planned_date=date(2026, 6, 12))
    move(db_session, started.id, "start")
    done = make_change(db_session, title="Late but done", planned_date=date(2026, 6, 5))
    move(db_session, done.id, "implement")
    make_change(db_session, title="On time", planned_date=date(2026, 9, 1))

    assert change_service.overdue_count(db_session, TODAY) == 2
