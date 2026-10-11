from datetime import date

from app.core.change_tracking import exists_as_of, standing

PLANNED = date(2026, 6, 30)


def stand(**overrides):
    args = {
        "status": "planned",
        "started_on": None,
        "closed_on": None,
        "planned_date": PLANNED,
        "as_of": date(2026, 6, 15),
    }
    args.update(overrides)
    return standing(**args)


def test_a_change_before_its_planned_date_is_planned_and_not_overdue() -> None:
    result = stand()

    assert (result.state, result.overdue) == ("planned", False)


def test_the_planned_date_itself_is_not_late() -> None:
    assert stand(as_of=PLANNED).overdue is False
    assert stand(as_of=date(2026, 7, 1)).overdue is True


def test_a_started_change_is_in_progress_and_can_still_be_overdue() -> None:
    started = stand(status="in_progress", started_on=date(2026, 6, 1))
    assert (started.state, started.overdue) == ("in_progress", False)

    late = stand(status="in_progress", started_on=date(2026, 6, 1), as_of=date(2026, 7, 5))
    assert (late.state, late.overdue) == ("in_progress", True)


def test_work_counts_as_started_only_from_its_start_date() -> None:
    result = stand(status="in_progress", started_on=date(2026, 6, 20), as_of=date(2026, 6, 15))

    assert result.state == "planned"


def test_a_closed_change_is_never_overdue() -> None:
    done = stand(status="implemented", closed_on=date(2026, 7, 10), as_of=date(2026, 8, 1))
    cancelled = stand(status="cancelled", closed_on=date(2026, 7, 10), as_of=date(2026, 8, 1))

    assert (done.state, done.overdue) == ("implemented", False)
    assert (cancelled.state, cancelled.overdue) == ("cancelled", False)


def test_a_closure_counts_only_once_its_date_has_come() -> None:
    before = stand(
        status="implemented",
        started_on=date(2026, 6, 1),
        closed_on=date(2026, 7, 10),
        as_of=date(2026, 7, 9),
    )
    on_the_day = stand(
        status="implemented",
        started_on=date(2026, 6, 1),
        closed_on=date(2026, 7, 10),
        as_of=date(2026, 7, 10),
    )

    # Closed after PLANNED, so on the 9th it was still open and late.
    assert (before.state, before.overdue) == ("in_progress", True)
    assert (on_the_day.state, on_the_day.overdue) == ("implemented", False)


def test_a_change_exists_from_the_day_it_was_raised() -> None:
    assert exists_as_of(date(2026, 6, 15), date(2026, 6, 15)) is True
    assert exists_as_of(date(2026, 6, 16), date(2026, 6, 15)) is False
