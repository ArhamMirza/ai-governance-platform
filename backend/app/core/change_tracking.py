"""Where a planned change to the AI management system stands -- ISO/IEC
42001 6.3. Pure functions, computed live from the change's own dates, never
stored, so a standing can't disagree with them.

Everything is evaluated *as of* a date, using only what had happened by then:
a change not yet raised doesn't exist, one not yet started is only planned,
and one closed later is still open. That lets a past management review keep
showing the changes it looked at (9.3).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

ChangeState = Literal["planned", "in_progress", "implemented", "cancelled"]

# What closing a change can mean.
CLOSED_STATES: frozenset[str] = frozenset({"implemented", "cancelled"})


@dataclass(frozen=True)
class ChangeStanding:
    state: ChangeState
    overdue: bool


def exists_as_of(raised_on: date, as_of: date) -> bool:
    return raised_on <= as_of


def standing(
    *,
    status: str,
    started_on: date | None,
    closed_on: date | None,
    planned_date: date,
    as_of: date,
) -> ChangeStanding:
    """A closure only counts once its date has come, and a change counts as
    started only from `started_on`. Overdue means still open and past its
    planned date -- the planned date itself isn't late yet."""
    if status in CLOSED_STATES and closed_on is not None and closed_on <= as_of:
        return ChangeStanding(state=cast(ChangeState, status), overdue=False)
    state: ChangeState = (
        "in_progress" if started_on is not None and started_on <= as_of else "planned"
    )
    return ChangeStanding(state=state, overdue=planned_date < as_of)
