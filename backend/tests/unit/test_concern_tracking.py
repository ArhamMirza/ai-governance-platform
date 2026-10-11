from datetime import UTC, date, datetime, timedelta

import pytest

from app.core import concern_tracking as tracking
from app.core.attempt_limiter import AttemptLimiter
from app.core.exceptions import RateLimitedError


def test_a_new_code_has_the_right_length_and_only_unambiguous_characters() -> None:
    codes = [tracking.new_tracking_code() for _ in range(200)]

    assert all(len(code) == tracking.CODE_LENGTH for code in codes)
    assert all(set(code) <= set(tracking.ALPHABET) for code in codes)
    # No 0, O, 1, I or L to confuse when reading a code off a screen.
    assert not any(set(code) & set("01OIL") for code in codes)
    assert len(set(codes)) == len(codes)


def test_a_code_is_shown_in_groups_of_four() -> None:
    assert tracking.format_code("ABCDEFGHJKMN") == "ABCD-EFGH-JKMN"


@pytest.mark.parametrize(
    "typed",
    ["ABCD-EFGH-JKMN", "abcd-efgh-jkmn", " abcd efgh jkmn ", "ABCDEFGHJKMN", "abcd_efgh.jkmn"],
)
def test_a_code_matches_however_it_was_typed_back(typed: str) -> None:
    assert tracking.hash_code(typed) == tracking.hash_code("ABCDEFGHJKMN")


def test_different_codes_hash_differently_and_the_hash_hides_the_code() -> None:
    first, second = tracking.hash_code("ABCDEFGHJKMN"), tracking.hash_code("ABCDEFGHJKMP")

    assert first != second
    assert len(first) == 64
    assert "ABCDEFGHJKMN" not in first


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ABCD-EFGH-JKMN", True),
        ("abcdefghjkmn", True),
        ("ABCD-EFGH", False),
        ("", False),
        # A wrong length after the ambiguous characters are dropped.
        ("0000-OOOO-1111", False),
        ("ABCD-EFGH-JKMN-PQRS", False),
    ],
)
def test_what_looks_like_a_code(text: str, expected: bool) -> None:
    assert tracking.looks_like_a_code(text) is expected


RECEIVED = date(2026, 6, 1)


def test_a_concern_is_due_an_acknowledgement_by_the_end_of_the_window() -> None:
    assert tracking.acknowledge_by(RECEIVED, 7) == date(2026, 6, 8)


def test_the_last_day_of_the_window_is_not_late() -> None:
    assert tracking.awaiting_triage("received", RECEIVED, 7, date(2026, 6, 8)) is False
    assert tracking.awaiting_triage("received", RECEIVED, 7, date(2026, 6, 9)) is True


@pytest.mark.parametrize("status", ["under_review", "resolved", "not_actioned"])
def test_only_a_concern_nobody_has_picked_up_awaits_triage(status: str) -> None:
    assert tracking.awaiting_triage(status, RECEIVED, 7, date(2026, 12, 1)) is False


def test_a_shorter_window_falls_due_sooner() -> None:
    assert tracking.awaiting_triage("received", RECEIVED, 2, date(2026, 6, 4)) is True
    assert tracking.awaiting_triage("received", RECEIVED, 2, date(2026, 6, 3)) is False


NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def make_limiter() -> AttemptLimiter:
    return AttemptLimiter(max_failures=3, window=timedelta(minutes=15), message="Slow down.")


def test_the_limiter_allows_failures_up_to_the_cap_then_refuses() -> None:
    limiter = make_limiter()
    for _ in range(3):
        limiter.check("7", NOW)
        limiter.record_failure("7", NOW)

    with pytest.raises(RateLimitedError, match="Slow down"):
        limiter.check("7", NOW)


def test_one_persons_failures_dont_count_against_another() -> None:
    limiter = make_limiter()
    for _ in range(3):
        limiter.record_failure("7", NOW)

    limiter.check("8", NOW)


def test_failures_age_out_of_the_window() -> None:
    limiter = make_limiter()
    for _ in range(3):
        limiter.record_failure("7", NOW)

    # Just inside the window they still count; at its edge they've aged out.
    with pytest.raises(RateLimitedError):
        limiter.check("7", NOW + timedelta(minutes=14))
    limiter.check("7", NOW + timedelta(minutes=15))


def test_reset_clears_one_key_or_all() -> None:
    limiter = make_limiter()
    for key in ("7", "8"):
        for _ in range(3):
            limiter.record_failure(key, NOW)

    limiter.reset("7")
    limiter.check("7", NOW)
    with pytest.raises(RateLimitedError):
        limiter.check("8", NOW)
    limiter.reset()
    limiter.check("8", NOW)
