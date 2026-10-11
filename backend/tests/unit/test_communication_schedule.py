from datetime import date

from app.core.communication_schedule import is_overdue, next_due

TODAY = date(2026, 6, 15)


def test_the_first_is_due_on_its_first_due_date() -> None:
    assert next_due(3, date(2026, 7, 1), []) == date(2026, 7, 1)


def test_after_that_it_is_due_an_interval_on_from_the_latest_record() -> None:
    dates = [date(2026, 1, 10), date(2026, 4, 20), date(2026, 2, 1)]

    assert next_due(3, date(2026, 1, 1), dates) == date(2026, 7, 20)


def test_the_interval_clamps_to_a_shorter_month() -> None:
    assert next_due(1, date(2026, 1, 31), [date(2026, 1, 31)]) == date(2026, 2, 28)


def test_without_an_interval_it_is_event_driven_and_never_due() -> None:
    assert next_due(None, None, []) is None
    assert next_due(None, None, [date(2026, 1, 10)]) is None


def test_overdue_only_after_its_due_date() -> None:
    assert is_overdue(True, date(2026, 6, 14), TODAY) is True
    assert is_overdue(True, TODAY, TODAY) is False
    assert is_overdue(True, date(2026, 6, 16), TODAY) is False
    assert is_overdue(True, None, TODAY) is False


def test_a_communication_that_was_stopped_is_never_overdue() -> None:
    assert is_overdue(False, date(2026, 1, 1), TODAY) is False
