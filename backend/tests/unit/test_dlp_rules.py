"""What a data-loss-prevention rule may look for -- app.core.dlp_rules -- and
the enrollment key -- app.core.agent_key."""

import pytest

from app.core import agent_key
from app.core.dlp_rules import (
    BUILTIN_DETECTORS,
    MAX_KEYWORDS,
    MAX_PATTERN_LENGTH,
    validate_builtin,
    validate_keywords,
    validate_pattern,
)
from app.core.exceptions import ValidationError


@pytest.mark.parametrize(
    "pattern",
    [
        r"\bPROJ-\d{4}\b",
        r"(?:alpha|beta)-\d+",
        r"secret(?=\s*[:=])",
        r"foo(?!bar)",
        r"[A-Z]{3}\d{6}",
        r"\(?:",  # an escaped paren, not a group opener
        r"[(?]x",  # inside a character class
    ],
)
def test_ordinary_patterns_are_allowed(pattern: str) -> None:
    assert validate_pattern(f"  {pattern}  ") == pattern


@pytest.mark.parametrize(
    ("pattern", "why"),
    [
        ("", "empty"),
        ("   ", "blank"),
        ("(unclosed", "invalid"),
        ("a" * (MAX_PATTERN_LENGTH + 1), "too long"),
        ("a*", "matches empty text"),
        ("x?", "matches empty text"),
        ("(?<=foo)bar", "lookbehind"),
        ("(?P<name>x)y", "named group"),
        ("(?i)secret", "inline flag"),
        ("(?#comment)x", "comment"),
        (r"(\w)\1", "back-reference"),
        ("(a+)+", "nested repeat"),
        ("(.*a)*", "nested repeat"),
        ("(x+x+)+y", "nested repeat"),
        (r"(\d+)*end", "nested repeat"),
        (r"(a|b*){2,}", "nested repeat"),
    ],
)
def test_patterns_that_could_misbehave_in_a_browser_are_refused(pattern: str, why: str) -> None:
    with pytest.raises(ValidationError):
        validate_pattern(pattern)


def test_a_repeated_group_without_a_repeat_inside_is_fine() -> None:
    assert validate_pattern(r"(?:ab){2,3}c") == r"(?:ab){2,3}c"


def test_keywords_are_trimmed_and_deduplicated_ignoring_case() -> None:
    result = validate_keywords(
        ["  Project Falcon ", "project falcon", "PROJECT FALCON", "Acme Corp"]
    )

    assert result == ["Project Falcon", "Acme Corp"]


def test_blank_keywords_are_skipped_but_a_rule_needs_at_least_one() -> None:
    assert validate_keywords(["", "  ", "Falcon"]) == ["Falcon"]
    for empty in ([], ["", "   "], None):
        with pytest.raises(ValidationError):
            validate_keywords(empty)


@pytest.mark.parametrize("keyword", ["ab", "x" * 101])
def test_a_keyword_must_be_a_sensible_length(keyword: str) -> None:
    with pytest.raises(ValidationError):
        validate_keywords([keyword])


def test_there_is_a_limit_to_how_many_keywords_one_rule_holds() -> None:
    assert len(validate_keywords([f"client-{i}" for i in range(MAX_KEYWORDS)])) == MAX_KEYWORDS
    with pytest.raises(ValidationError):
        validate_keywords([f"client-{i}" for i in range(MAX_KEYWORDS + 1)])


def test_a_builtin_detector_must_be_one_that_exists() -> None:
    assert validate_builtin("credit_card") == "credit_card"
    for bad in (None, "", "credit-card", "nonsense"):
        with pytest.raises(ValidationError):
            validate_builtin(bad)


def test_every_builtin_detector_has_a_label_and_a_description() -> None:
    assert len(BUILTIN_DETECTORS) >= 8
    for key, (label, description) in BUILTIN_DETECTORS.items():
        assert key == key.lower() and label and description


def test_a_new_key_is_long_random_and_prefixed() -> None:
    first, second = agent_key.new_enrollment_key(), agent_key.new_enrollment_key()

    assert first != second
    assert first.startswith("aigk_") and len(first) > 40


def test_a_key_matches_only_its_own_hash() -> None:
    key = agent_key.new_enrollment_key()
    stored = agent_key.hash_key(key)

    assert agent_key.key_matches(key, stored)
    assert agent_key.key_matches(f"  {key}\n", stored)  # whitespace from a pasted header
    assert not agent_key.key_matches(key + "x", stored)
    assert not agent_key.key_matches(agent_key.new_enrollment_key(), stored)
    assert not agent_key.key_matches("", stored)


def test_no_key_issued_matches_nothing() -> None:
    assert not agent_key.key_matches("anything", None)
    assert not agent_key.key_matches("", None)
    assert not agent_key.key_matches("", "")


def test_the_stored_hash_does_not_reveal_the_key() -> None:
    key = agent_key.new_enrollment_key()

    assert key not in agent_key.hash_key(key)
    assert len(agent_key.hash_key(key)) == 64
    assert agent_key.hint(key) == key[-4:]
