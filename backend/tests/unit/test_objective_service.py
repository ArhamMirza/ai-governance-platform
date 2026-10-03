from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.repositories import objective_repository
from app.schemas.objective import (
    MeasurementCreate,
    ObjectiveClose,
    ObjectiveCreate,
    ObjectiveUpdate,
)
from app.schemas.policy import PolicyCreate
from app.services import (
    ai_system_inventory_service,
    framework_service,
    objective_service,
    policy_service,
)

TODAY = date(2026, 6, 15)


def make_ai_system(db: Session, name: str = "Resume Screener") -> int:
    return ai_system_inventory_service.add_row(db, {"name": name}, actor_id=None).id


def make_measured(db: Session, **overrides):
    data = {
        "title": "Bias test pass rate",
        "kind": "measured",
        "established_on": date(2026, 1, 1),
        "target_date": date(2026, 12, 31),
        "metric_name": "Bias test pass rate",
        "unit": "%",
        "direction": "at_least",
        "target_value": 95,
        "measurement_interval_months": 3,
        "first_measurement_due": date(2026, 3, 31),
    }
    data.update(overrides)
    return objective_service.create_objective(db, ObjectiveCreate(**data), actor_id=None)


def make_milestone(db: Session, **overrides):
    data = {
        "title": "Publish an AI transparency notice",
        "kind": "milestone",
        "established_on": date(2026, 1, 1),
        "target_date": date(2026, 9, 30),
    }
    data.update(overrides)
    return objective_service.create_objective(db, ObjectiveCreate(**data), actor_id=None)


def record(db: Session, objective_id: int, measured_on: date, value: float):
    return objective_service.record_measurement(
        db,
        objective_id,
        MeasurementCreate(measured_on=measured_on, value=value),
        actor_id=None,
        today=TODAY,
    )


def test_established_on_defaults_to_today(db_session: Session) -> None:
    objective = objective_service.create_objective(
        db_session,
        ObjectiveCreate(title="Notice", kind="milestone", target_date=date(2026, 9, 30)),
        actor_id=None,
        today=TODAY,
    )

    assert objective.established_on == TODAY
    assert objective.status == "active"


@pytest.mark.parametrize(
    "overrides",
    [
        {"metric_name": None},
        {"direction": None},
        {"target_value": None},
        {"first_measurement_due": None},  # Interval without a first due date.
        {"target_date": date(2025, 12, 31)},  # Before it was set.
    ],
)
def test_a_measured_objective_must_be_complete(db_session: Session, overrides) -> None:
    with pytest.raises(ValidationError):
        make_measured(db_session, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [{"metric_name": "Pass rate"}, {"target_value": 1}, {"target_date": None}],
)
def test_a_milestone_has_no_metric_but_needs_a_target_date(db_session: Session, overrides) -> None:
    with pytest.raises(ValidationError):
        make_milestone(db_session, **overrides)


def test_an_unknown_policy_is_refused(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        make_milestone(db_session, policy_id=999)


def test_a_failed_update_leaves_the_objective_unchanged(db_session: Session) -> None:
    objective = make_measured(db_session)

    with pytest.raises(ValidationError):
        objective_service.update_objective(
            db_session, objective.id, ObjectiveUpdate(target_value=None), actor_id=None
        )

    assert objective_service.get_objective(db_session, objective.id).target_value == 95


def test_a_measured_objective_with_readings_cant_become_a_milestone(db_session: Session) -> None:
    objective = make_measured(db_session)
    record(db_session, objective.id, date(2026, 3, 1), 90)

    with pytest.raises(ValidationError):
        objective_service.update_objective(
            db_session, objective.id, ObjectiveUpdate(kind="milestone"), actor_id=None
        )


def test_readings_drive_the_standing(db_session: Session) -> None:
    objective = make_measured(db_session)
    record(db_session, objective.id, date(2026, 3, 1), 90)
    record(db_session, objective.id, date(2026, 6, 1), 96)
    readings = objective_service.list_measurements(db_session, objective.id)

    assert objective_service.standing(objective, readings, date(2026, 5, 1)).state == "off_track"
    assert objective_service.standing(objective, readings, TODAY).state == "on_track"


def test_a_reading_cant_be_in_the_future_or_on_a_milestone(db_session: Session) -> None:
    objective = make_measured(db_session)
    milestone = make_milestone(db_session)

    with pytest.raises(ValidationError):
        record(db_session, objective.id, date(2026, 6, 16), 96)
    with pytest.raises(ValidationError):
        record(db_session, milestone.id, date(2026, 6, 1), 1)


def test_a_closed_objective_takes_no_readings_until_reopened(db_session: Session) -> None:
    objective = make_measured(db_session)
    objective_service.close_objective(
        db_session, objective.id, ObjectiveClose(status="withdrawn"), actor_id=None, today=TODAY
    )

    with pytest.raises(InvalidStatusTransitionError):
        record(db_session, objective.id, date(2026, 6, 1), 96)

    reopened = objective_service.reopen_objective(db_session, objective.id, actor_id=None)
    assert (reopened.status, reopened.closed_on) == ("active", None)
    record(db_session, objective.id, date(2026, 6, 1), 96)


def test_closing_is_dated_and_only_happens_once(db_session: Session) -> None:
    objective = make_milestone(db_session)

    closed = objective_service.close_objective(
        db_session,
        objective.id,
        ObjectiveClose(status="achieved", closure_note="Published"),
        actor_id=None,
        today=TODAY,
    )

    assert (closed.status, closed.closed_on, closed.closure_note) == (
        "achieved",
        TODAY,
        "Published",
    )
    with pytest.raises(InvalidStatusTransitionError):
        objective_service.close_objective(
            db_session, objective.id, ObjectiveClose(status="withdrawn"), actor_id=None
        )
    with pytest.raises(ValidationError):
        objective_service.close_objective(
            db_session, make_milestone(db_session).id, ObjectiveClose(status="active"), None
        )


def test_an_objective_with_readings_cant_be_deleted(db_session: Session) -> None:
    objective = make_measured(db_session)
    record(db_session, objective.id, date(2026, 3, 1), 90)

    with pytest.raises(InvalidStatusTransitionError):
        objective_service.delete_objective(db_session, objective.id, actor_id=None)


def test_deleting_an_objective_removes_its_links_and_tags(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    objective = make_milestone(db_session)
    objective_service.set_ai_systems(db_session, objective.id, [row_id], actor_id=None)

    objective_service.delete_objective(db_session, objective.id, actor_id=None)

    assert objective_repository.list_links_for_ai_system(db_session, row_id) == []
    assert framework_service.get_tags(db_session, "AIObjective", objective.id) == []


def test_relinking_keeps_surviving_links(db_session: Session) -> None:
    first, second, third = (make_ai_system(db_session, name) for name in ("A", "B", "C"))
    objective = make_milestone(db_session)
    objective_service.set_ai_systems(db_session, objective.id, [first, second], actor_id=None)
    kept = {
        link.ai_system_row_id: link.id
        for link in objective_repository.list_links_for_objective(db_session, objective.id)
    }

    objective_service.set_ai_systems(db_session, objective.id, [second, third], actor_id=None)

    links = objective_repository.list_links_for_objective(db_session, objective.id)
    assert [link.ai_system_row_id for link in links] == [second, third]
    assert next(link.id for link in links if link.ai_system_row_id == second) == kept[second]


def test_linking_an_unknown_ai_system_is_refused(db_session: Session) -> None:
    objective = make_milestone(db_session)

    with pytest.raises(NotFoundError):
        objective_service.set_ai_systems(db_session, objective.id, [999], actor_id=None)


def test_filtering_by_ai_system(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    linked = make_milestone(db_session, title="Linked")
    make_milestone(db_session, title="Not linked")
    objective_service.set_ai_systems(db_session, linked.id, [row_id], actor_id=None)

    assert [o.title for o in objective_service.list_objectives(db_session, row_id)] == ["Linked"]


def test_deleting_an_ai_system_unlinks_it_without_deleting_the_objective(
    db_session: Session,
) -> None:
    row_id = make_ai_system(db_session)
    objective = make_milestone(db_session)
    objective_service.set_ai_systems(db_session, objective.id, [row_id], actor_id=None)

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    assert objective_service.get_objective(db_session, objective.id).title
    assert objective_service.linked_ai_system_ids(db_session, objective.id) == []


def test_deleting_a_draft_policy_clears_the_reference(db_session: Session) -> None:
    policy = policy_service.create_policy(db_session, PolicyCreate(title="AI Policy"), None)
    objective = make_milestone(db_session, policy_id=policy.id)

    policy_service.delete_policy(db_session, policy.id, actor_id=None)

    assert objective_service.get_objective(db_session, objective.id).policy_id is None


def test_standings_as_of_skip_objectives_set_later(db_session: Session) -> None:
    early = make_measured(db_session, title="Early")
    make_milestone(db_session, title="Later", established_on=date(2026, 5, 1))
    record(db_session, early.id, date(2026, 2, 1), 90)
    record(db_session, early.id, date(2026, 4, 15), 97)

    as_of_march = objective_service.standings_as_of(db_session, date(2026, 3, 1))

    assert [(o.title, s.state) for o, s in as_of_march] == [("Early", "off_track")]
    as_of_today = objective_service.standings_as_of(db_session, TODAY)
    assert {o.title: s.state for o, s in as_of_today} == {
        "Early": "on_track",
        "Later": "in_progress",
    }


def test_attention_counts(db_session: Session) -> None:
    off_track = make_measured(db_session, title="Off track")
    record(db_session, off_track.id, date(2026, 6, 1), 80)
    make_measured(db_session, title="Never measured")  # First due 2026-03-31 -- overdue.
    on_track = make_measured(db_session, title="On track")
    record(db_session, on_track.id, date(2026, 6, 1), 99)
    make_milestone(db_session, title="Missed", target_date=date(2026, 6, 1))
    closed = make_milestone(db_session, title="Closed", target_date=date(2026, 6, 1))
    objective_service.close_objective(
        db_session, closed.id, ObjectiveClose(status="not_achieved"), None, today=TODAY
    )

    counts = objective_service.attention_counts(db_session, TODAY)

    assert (counts.falling_short, counts.measurement_overdue) == (2, 1)
