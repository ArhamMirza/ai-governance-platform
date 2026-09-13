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

from collections.abc import Callable, Collection, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy import update
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


def claim_transition(
    db: Session,
    record: Any,
    *,
    expected_statuses: str | Collection[str],
    changes: dict[str, Any],
) -> bool:
    """Move a record on, but only from the status the caller just checked.

    Returns whether this call is the one that moved it. False means someone
    else got there first -- their transition stands, and this one has changed
    nothing.

    An approval is a read-check-write like any other: two approvers both find
    a record pending, both pass every gate, and both write. Without the
    status in the WHERE clause, the second write simply lands on top of the
    first and the record ends up recording whichever approver happened to
    commit last. With it, the second write matches no rows.

    It also closes a subtler hole. Two simultaneous submissions each write a
    "submitted_for_review" audit entry, and require_different_approver reads
    only the latest -- so the earlier submitter could then approve their own
    work. One submission landing means one such entry."""
    model = type(record)
    allowed = (
        [expected_statuses]
        if isinstance(expected_statuses, str)
        else list(expected_statuses)
    )
    return _write_transition(db, record, model.status.in_(allowed), changes)


def claim_if_unset(db: Session, record: Any, *, column: str, changes: dict[str, Any]) -> bool:
    """Write only if `column` is still empty; report whether this call is the
    one that filled it.

    For records whose transition is marked by a field rather than a status --
    a release approval is "the row that has an approver in it". Guards
    against a second approval at all, not only a simultaneous one: without
    it, approving twice quietly replaces whoever signed off first."""
    model = type(record)
    return _write_transition(db, record, getattr(model, column).is_(None), changes)


def withdraw_transition(db: Session, record: Any, changes: dict[str, Any]) -> None:
    """Put a record back to draft whatever state it is in now.

    The opposite of claim_transition, and deliberately unguarded. Withdrawal
    is what an edit does to an approval, and it has to win from any status:
    if an approval commits between this caller reading the record and writing
    it, the withdrawal still has to take that approval down -- it describes
    content that has since changed. Guarding it on the status that was read
    would let exactly that pairing through.

    Unguarded either way round, the two orderings both end safe: withdraw
    last and the approval is cleared; withdraw first and the approver's own
    claim_transition finds the wrong status and is refused.

    It writes every field rather than assigning them on the instance for the
    same reason: the instance can be a moment behind the table, and the ORM
    only writes attributes whose value it can see changing. Setting
    approved_by to None on an instance that was loaded before the approval
    landed looks like no change at all, and the approver's name would stay in
    the row under a draft status."""
    _write_transition(db, record, None, changes)


def _write_transition(db: Session, record: Any, guard, changes: dict[str, Any]) -> bool:
    model = type(record)
    statement = update(model).where(model.id == record.id)
    if guard is not None:
        statement = statement.where(guard)
    written = db.execute(statement.values(**changes)).rowcount == 1
    db.commit()
    # The UPDATE went round the instance, so its attributes are still whatever
    # they were when the caller read them -- including, when this call lost, a
    # status that is now out of date.
    db.refresh(record)
    return written


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
