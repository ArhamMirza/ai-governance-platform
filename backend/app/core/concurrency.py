"""Helpers for the window between checking and writing.

Every repository commits as it writes, so a service that reads, finds
nothing, and then inserts does the two halves in separate transactions. Two
simultaneous requests therefore both read nothing and both insert -- and
since FastAPI runs this app's sync endpoints in a threadpool, "simultaneous"
is reachable with a single worker.

A unique constraint is what actually stops the duplicate; these helpers turn
the constraint violation the loser gets into the answer it was after (the
row the winner created) or into the same ConflictError a sequential caller
would have seen, rather than a 500.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError

T = TypeVar("T")


def create_or_get(db: Session, factory: Callable[[], T], lookup: Callable[[], T | None]) -> T:
    """Insert the row, or return the one a simultaneous request just inserted.

    For get-or-create records that exist purely to carry state for something
    else -- a lifecycle for an AI system, a review record for a dataset. Both
    callers wanted the same row to exist, so handing the loser the winner's
    row is the outcome each of them asked for."""
    try:
        instance = factory()
        db.add(instance)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = lookup()
        if existing is None:
            # Not the race we absorb -- a bad foreign key, say. The row still
            # doesn't exist, so there is nothing to hand back.
            raise
        return existing
    db.refresh(instance)
    return instance


@contextmanager
def conflict_on_duplicate(db: Session, message: str) -> Iterator[None]:
    """Report a lost insert race as the caller's own duplicate conflict.

    For records where a duplicate is a mistake to report rather than a row to
    share -- a second risk assessment for one AI system. The caller has
    already checked and found none; this covers the gap between that check
    and the insert, and says the same thing that check would have."""
    try:
        yield
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message) from exc
