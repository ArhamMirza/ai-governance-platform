"""Where an AI objective stands -- ISO/IEC 42001 6.2 and 9.1. Pure functions,
computed live from the objective's own fields and its recorded readings,
never stored, so the standing can't disagree with them.

Everything is evaluated *as of* a date, using only what was known by then:
readings taken on or before it, and the objective's closure only once it
had happened. That's what lets a past management review keep showing the
standing it reviewed (9.3), however many readings have arrived since.

Measurement timing is the same rule as internal audits and supplier reviews
(app.core.audit_schedule): due on first_measurement_due until the first
reading, then interval_months on from the latest one.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

from app.core import audit_schedule

ObjectiveState = Literal[
    # Active objectives -- computed.
    "not_measured",  # Measured kind, no reading yet.
    "on_track",  # The latest reading meets the target.
    "off_track",  # The latest reading misses it; the target date hasn't passed.
    "missed",  # The target date has passed without the target being met.
    "in_progress",  # Milestone kind, before its target date.
    # Closed objectives -- the person's decision, as recorded.
    "achieved",
    "not_achieved",
    "withdrawn",
]

# States an active objective is in when it needs someone's attention.
FALLING_SHORT: frozenset[str] = frozenset({"off_track", "missed"})


@dataclass(frozen=True)
class Reading:
    measured_on: date
    value: float


@dataclass(frozen=True)
class Standing:
    state: ObjectiveState
    latest_value: float | None
    latest_on: date | None
    next_measurement_due: date | None
    measurement_overdue: bool


def meets_target(value: float, direction: str, target: float) -> bool:
    """`at_least` targets are met from the target up, `at_most` from it
    down -- landing exactly on the target meets it either way."""
    if direction == "at_most":
        return value <= target
    return value >= target


def next_measurement_due(
    interval_months: int | None, first_measurement_due: date | None, reading_dates: list[date]
) -> date | None:
    if interval_months is None:
        return None
    if not reading_dates:
        return first_measurement_due
    return audit_schedule.next_audit_date(max(reading_dates), interval_months)


def standing(
    *,
    kind: str,
    status: str,
    closed_on: date | None,
    direction: str | None,
    target_value: float | None,
    target_date: date | None,
    interval_months: int | None,
    first_measurement_due: date | None,
    readings: list[Reading],
    as_of: date,
) -> Standing:
    """`readings` in the order they were recorded; of two taken the same
    day, the later-recorded one is the latest."""
    known = sorted((r for r in readings if r.measured_on <= as_of), key=lambda r: r.measured_on)
    latest = known[-1] if known else None
    latest_value = latest.value if latest else None
    latest_on = latest.measured_on if latest else None

    if status != "active" and closed_on is not None and closed_on <= as_of:
        return Standing(cast(ObjectiveState, status), latest_value, latest_on, None, False)

    target_passed = target_date is not None and target_date < as_of

    if kind == "milestone":
        return Standing(
            "missed" if target_passed else "in_progress", latest_value, latest_on, None, False
        )

    next_due = next_measurement_due(
        interval_months, first_measurement_due, [r.measured_on for r in known]
    )
    overdue = audit_schedule.is_audit_overdue(next_due, as_of)

    state: ObjectiveState
    if (
        latest is not None
        and target_value is not None
        and direction is not None
        and (meets_target(latest.value, direction, target_value))
    ):
        state = "on_track"
    elif target_passed:
        state = "missed"
    elif latest is None:
        state = "not_measured"
    else:
        state = "off_track"
    return Standing(state, latest_value, latest_on, next_due, overdue)
