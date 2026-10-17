"""Where an improvement stands, as of a date -- app.core.improvement_tracking."""

from datetime import date

import pytest

from app.core.improvement_tracking import standing

TARGET = date(2026, 6, 30)


def stand(as_of: date, **fields):
    defaults = {"status": "proposed", "decided_on": None, "closed_on": None}
    return standing(**{**defaults, **fields}, target_date=TARGET, as_of=as_of)


def test_a_proposal_is_proposed_and_on_time_up_to_its_target_date() -> None:
    result = stand(TARGET)

    assert (result.state, result.overdue) == ("proposed", False)


def test_the_day_after_the_target_date_an_open_improvement_is_overdue() -> None:
    assert stand(date(2026, 7, 1)).overdue is True
    assert stand(date(2026, 7, 1), status="accepted", decided_on=date(2026, 6, 1)).overdue is True


def test_it_counts_as_accepted_only_from_the_day_it_was_decided() -> None:
    accepted = {"status": "accepted", "decided_on": date(2026, 6, 10)}

    assert stand(date(2026, 6, 9), **accepted).state == "proposed"
    assert stand(date(2026, 6, 10), **accepted).state == "accepted"


@pytest.mark.parametrize("status", ["implemented", "declined"])
def test_a_closure_counts_from_its_date_and_is_never_overdue(status: str) -> None:
    closed = {"status": status, "decided_on": date(2026, 6, 1), "closed_on": date(2026, 7, 5)}

    before = stand(date(2026, 7, 4), **closed)
    after = stand(date(2026, 8, 1), **closed)

    # Still open the day before it closed -- and past its target by then.
    assert (before.state, before.overdue) == ("accepted", True)
    assert (after.state, after.overdue) == (status, False)


def test_a_closed_status_with_no_closing_date_is_not_treated_as_closed() -> None:
    assert stand(TARGET, status="implemented").state == "proposed"
