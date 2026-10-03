from datetime import date

import pytest

from app.core.objective_tracking import Reading, meets_target, next_measurement_due, standing

AS_OF = date(2026, 6, 15)


def measured(**overrides):
    args = {
        "kind": "measured",
        "status": "active",
        "closed_on": None,
        "direction": "at_least",
        "target_value": 95.0,
        "target_date": date(2026, 12, 31),
        "interval_months": 3,
        "first_measurement_due": date(2026, 3, 31),
        "readings": [],
        "as_of": AS_OF,
    }
    args.update(overrides)
    return standing(**args)


def milestone(**overrides):
    args = {
        "kind": "milestone",
        "status": "active",
        "closed_on": None,
        "direction": None,
        "target_value": None,
        "target_date": date(2026, 9, 30),
        "interval_months": None,
        "first_measurement_due": None,
        "readings": [],
        "as_of": AS_OF,
    }
    args.update(overrides)
    return standing(**args)


@pytest.mark.parametrize(
    ("value", "direction", "met"),
    [
        (96, "at_least", True),
        (95, "at_least", True),
        (94.9, "at_least", False),
        (4, "at_most", True),
        (5, "at_most", True),
        (5.1, "at_most", False),
    ],
)
def test_meets_target_in_both_directions_including_exactly_on_it(value, direction, met) -> None:
    assert meets_target(value, direction, 95 if direction == "at_least" else 5) is met


def test_next_measurement_is_due_on_first_due_until_the_first_reading() -> None:
    assert next_measurement_due(3, date(2026, 3, 31), []) == date(2026, 3, 31)
    assert next_measurement_due(3, date(2026, 3, 31), [date(2026, 4, 10), date(2026, 2, 1)]) == (
        date(2026, 7, 10)
    )
    assert next_measurement_due(None, None, [date(2026, 4, 10)]) is None


def test_a_reading_meeting_the_target_is_on_track() -> None:
    result = measured(readings=[Reading(date(2026, 5, 1), 96.0)])

    assert result.state == "on_track"
    assert result.latest_value == 96.0
    assert result.latest_on == date(2026, 5, 1)


def test_a_reading_missing_the_target_before_the_target_date_is_off_track() -> None:
    assert measured(readings=[Reading(date(2026, 5, 1), 90.0)]).state == "off_track"


def test_missing_the_target_once_the_target_date_has_passed_is_missed() -> None:
    result = measured(target_date=date(2026, 6, 1), readings=[Reading(date(2026, 5, 1), 90.0)])

    assert result.state == "missed"


def test_meeting_the_target_after_the_target_date_is_still_on_track() -> None:
    result = measured(target_date=date(2026, 6, 1), readings=[Reading(date(2026, 5, 1), 97.0)])

    assert result.state == "on_track"


def test_no_reading_yet_is_not_measured_and_overdue_once_first_due_passes() -> None:
    result = measured()

    assert result.state == "not_measured"
    assert result.next_measurement_due == date(2026, 3, 31)
    assert result.measurement_overdue is True
    assert measured(as_of=date(2026, 3, 31)).measurement_overdue is False


def test_overdue_runs_from_the_latest_reading() -> None:
    readings = [Reading(date(2026, 1, 15), 96.0), Reading(date(2026, 3, 1), 96.0)]

    assert measured(readings=readings, as_of=date(2026, 6, 1)).measurement_overdue is False
    late = measured(readings=readings, as_of=date(2026, 6, 2))
    assert late.next_measurement_due == date(2026, 6, 1)
    assert late.measurement_overdue is True


def test_readings_after_the_as_of_date_are_ignored() -> None:
    readings = [Reading(date(2026, 4, 1), 90.0), Reading(date(2026, 7, 1), 99.0)]

    then = measured(readings=readings, as_of=AS_OF)
    assert then.state == "off_track"
    assert then.latest_value == 90.0
    assert measured(readings=readings, as_of=date(2026, 7, 1)).state == "on_track"


def test_of_two_readings_the_same_day_the_later_recorded_one_counts() -> None:
    readings = [Reading(date(2026, 5, 1), 99.0), Reading(date(2026, 5, 1), 80.0)]

    assert measured(readings=readings).latest_value == 80.0


def test_a_milestone_is_in_progress_until_its_target_date_then_missed() -> None:
    assert milestone(as_of=date(2026, 9, 30)).state == "in_progress"
    assert milestone(as_of=date(2026, 10, 1)).state == "missed"
    assert milestone().measurement_overdue is False


def test_a_closed_objective_reports_how_it_was_closed() -> None:
    result = measured(status="achieved", closed_on=date(2026, 6, 1))

    assert result.state == "achieved"
    assert result.measurement_overdue is False


def test_before_it_was_closed_an_objective_still_stands_as_it_did() -> None:
    result = measured(
        status="withdrawn",
        closed_on=date(2026, 7, 1),
        readings=[Reading(date(2026, 5, 1), 90.0)],
    )

    assert result.state == "off_track"
