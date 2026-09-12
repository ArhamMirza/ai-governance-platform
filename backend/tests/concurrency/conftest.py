"""A harness for tests that need two requests genuinely in flight at once.

The ordinary db_session fixture can't express this: it is ":memory:" on a
StaticPool, so every caller shares one connection and therefore one
transaction -- two threads there can't be two concurrent transactions no
matter how they're scheduled. These tests get a file-backed database and a
session per thread instead.

Interleaving is forced, not hoped for. `pause_after` holds each thread at a
barrier the first time it runs the read a service checks against, so no
thread reaches its write until every thread has finished reading -- which is
exactly the state two simultaneous requests arrive in, and the state that
makes a read-check-write race reproducible instead of occasional.
"""

import threading
from collections.abc import Callable, Generator, Iterator
from typing import Any, NamedTuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from tests.conftest import seed_reference_data

# Long enough that a loaded CI machine doesn't trip it, short enough that a
# genuine deadlock fails the test instead of hanging the suite.
BARRIER_TIMEOUT_SECONDS = 15


class Outcome(NamedTuple):
    """What one thread came back with -- exactly one of these is set."""

    value: Any
    error: BaseException | None


@pytest.fixture()
def concurrent_sessions(tmp_path) -> Generator[Callable[[], Session], None, None]:
    """A factory for independent sessions onto one file-backed database.

    Each thread must take its own: a Session is not safe to share, and two
    threads on one session would be back to a single transaction."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrency.db'}",
        # The threads block on each other by design; without a busy timeout
        # the loser of a write lock fails instantly with "database is locked"
        # instead of waiting its turn the way a real request would.
        connect_args={"check_same_thread": False, "timeout": 20},
    )
    Base.metadata.create_all(bind=engine)
    make_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    setup = make_session()
    try:
        seed_reference_data(setup)
    finally:
        setup.close()

    yield make_session
    engine.dispose()


@pytest.fixture()
def setup_session(concurrent_sessions) -> Generator[Session, None, None]:
    """For building the fixture data a race runs against. Committed and
    closed before the threads start, so they read it from the database
    rather than from a session someone else is still holding."""
    session = concurrent_sessions()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def pause_after(monkeypatch, target, attribute: str, barrier: threading.Barrier) -> None:
    """Hold every thread at `barrier` the first time it calls `attribute`.

    Point this at the read a service checks against -- the look-up that comes
    back empty -- and every thread will have finished checking before any of
    them writes. Only the first call per thread waits: services call these
    look-ups more than once, and tripping the barrier again would either
    hang or let the threads drift back out of step.

    The patch outlives the race (monkeypatch undoes it at the end of the
    test), so the calling thread is exempt -- otherwise a test that checks
    the result by calling the same function would sit down at a barrier
    nobody else is coming to."""
    original = getattr(target, attribute)
    installed_by = threading.get_ident()
    local = threading.local()

    def paused(*args, **kwargs):
        result = original(*args, **kwargs)
        if threading.get_ident() != installed_by and not getattr(local, "waited", False):
            local.waited = True
            barrier.wait(timeout=BARRIER_TIMEOUT_SECONDS)
        return result

    monkeypatch.setattr(target, attribute, paused)


def run_together(
    concurrent_sessions: Callable[[], Session],
    work: Callable[[Session, int], Any],
    count: int = 2,
) -> list[Outcome]:
    """Run `work(session, index)` in `count` threads, one session each.

    Returns an Outcome per thread in index order: what it returned, or what
    it raised. Both halves matter -- a race is fixed only when the winner
    gets the right answer *and* the loser gets a clean conflict."""
    outcomes: list[Outcome | None] = [None] * count

    def run(index: int) -> None:
        session = concurrent_sessions()
        try:
            outcomes[index] = Outcome(work(session, index), None)
        except BaseException as exc:  # noqa: BLE001 -- reported, not swallowed
            outcomes[index] = Outcome(None, exc)
        finally:
            session.close()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=BARRIER_TIMEOUT_SECONDS * 2)

    still_running = [thread for thread in threads if thread.is_alive()]
    assert not still_running, f"{len(still_running)} thread(s) never finished"
    return [outcome for outcome in outcomes if outcome is not None]


def errors(outcomes: list[Outcome]) -> Iterator[BaseException]:
    return (outcome.error for outcome in outcomes if outcome.error is not None)


def barrier(count: int = 2) -> threading.Barrier:
    return threading.Barrier(count, timeout=BARRIER_TIMEOUT_SECONDS)
