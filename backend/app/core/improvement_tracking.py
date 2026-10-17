"""Where an opportunity for improvement stands -- ISO/IEC 42001 10.1. Pure
functions, computed live from the improvement's own dates, never stored, so
a standing can't disagree with them.

Everything is evaluated *as of* a date, using only what had happened by
then, the same way app.core.change_tracking does: an improvement not yet
raised doesn't exist, one accepted later was still proposed, and one closed
later was still open. That lets a past management review keep showing the
improvements it looked at (9.3).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

from app.core.change_tracking import exists_as_of

ImprovementState = Literal["proposed", "accepted", "implemented", "declined"]

CLOSED_STATES: frozenset[str] = frozenset({"implemented", "declined"})

__all__ = ["CLOSED_STATES", "ImprovementStanding", "ImprovementState", "exists_as_of", "standing"]


@dataclass(frozen=True)
class ImprovementStanding:
    state: ImprovementState
    overdue: bool


def standing(
    *,
    status: str,
    decided_on: date | None,
    closed_on: date | None,
    target_date: date,
    as_of: date,
) -> ImprovementStanding:
    """A closure only counts once its date has come, and an improvement
    counts as accepted only from `decided_on`. Overdue means still open --
    proposed or accepted -- and past its target date; the target date
    itself isn't late yet."""
    if status in CLOSED_STATES and closed_on is not None and closed_on <= as_of:
        return ImprovementStanding(state=cast(ImprovementState, status), overdue=False)
    state: ImprovementState = (
        "accepted" if decided_on is not None and decided_on <= as_of else "proposed"
    )
    return ImprovementStanding(state=state, overdue=target_date < as_of)
