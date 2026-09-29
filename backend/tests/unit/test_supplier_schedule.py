from datetime import date

from app.core import supplier_schedule

TODAY = date(2026, 6, 15)


def test_no_interval_means_no_review_is_ever_due() -> None:
    assert supplier_schedule.next_review_due(None, None, [date(2020, 1, 1)]) is None


def test_the_first_review_is_due_on_its_own_date() -> None:
    assert supplier_schedule.next_review_due(12, date(2026, 3, 1), []) == date(2026, 3, 1)


def test_later_reviews_are_due_an_interval_after_the_latest() -> None:
    assert supplier_schedule.next_review_due(
        12, date(2024, 1, 1), [date(2025, 2, 1), date(2025, 9, 10)]
    ) == date(2026, 9, 10)


def test_not_overdue_on_the_due_date_itself() -> None:
    assert not supplier_schedule.is_review_overdue(True, TODAY, TODAY)


def test_overdue_the_day_after() -> None:
    assert supplier_schedule.is_review_overdue(True, date(2026, 6, 14), TODAY)


def test_an_inactive_supplier_is_never_overdue() -> None:
    assert not supplier_schedule.is_review_overdue(False, date(2020, 1, 1), TODAY)


def test_a_contract_past_its_end_date_has_expired() -> None:
    assert supplier_schedule.contract_status(True, date(2026, 6, 14), TODAY) == "expired"


def test_a_contract_ending_today_is_expiring_not_expired() -> None:
    assert supplier_schedule.contract_status(True, TODAY, TODAY) == "expiring"


def test_a_contract_ending_exactly_30_days_out_is_expiring() -> None:
    assert supplier_schedule.contract_status(True, date(2026, 7, 15), TODAY) == "expiring"


def test_a_contract_ending_31_days_out_is_fine() -> None:
    assert supplier_schedule.contract_status(True, date(2026, 7, 16), TODAY) is None


def test_no_end_date_never_alerts() -> None:
    assert supplier_schedule.contract_status(True, None, TODAY) is None


def test_an_inactive_supplier_never_alerts() -> None:
    assert supplier_schedule.contract_status(False, date(2020, 1, 1), TODAY) is None
