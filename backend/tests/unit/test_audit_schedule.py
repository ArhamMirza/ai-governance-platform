from datetime import date

from app.core import audit_schedule


def test_next_audit_date_adds_whole_months() -> None:
    assert audit_schedule.next_audit_date(date(2026, 1, 15), 6) == date(2026, 7, 15)


def test_next_audit_date_rolls_over_the_year() -> None:
    assert audit_schedule.next_audit_date(date(2026, 10, 1), 6) == date(2027, 4, 1)


def test_next_audit_date_clamps_to_a_shorter_month() -> None:
    # Jan 31 + 1 month has no Feb 31 -- clamps to the last day of February.
    assert audit_schedule.next_audit_date(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_next_audit_date_handles_a_multi_year_interval() -> None:
    assert audit_schedule.next_audit_date(date(2026, 3, 1), 24) == date(2028, 3, 1)


def test_is_audit_overdue_true_when_due_date_passed() -> None:
    assert audit_schedule.is_audit_overdue(date(2026, 1, 1), date(2026, 1, 2)) is True


def test_is_audit_overdue_false_when_due_date_in_future() -> None:
    assert audit_schedule.is_audit_overdue(date(2026, 1, 2), date(2026, 1, 1)) is False


def test_is_audit_overdue_false_when_no_due_date() -> None:
    assert audit_schedule.is_audit_overdue(None, date(2026, 1, 1)) is False
