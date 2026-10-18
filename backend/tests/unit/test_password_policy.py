import pytest

from app.core import password_policy
from app.core.exceptions import ValidationError


@pytest.mark.parametrize(
    "password",
    [
        "correct horse battery staple",
        "tangerine-lantern-47-meadow",
        "Xk9#mP2$vL8@qR4!",
        "purple-giraffe-eats-pizza",
    ],
)
def test_a_long_varied_password_is_accepted(password: str) -> None:
    assert password_policy.problem_with(password) is None


def test_the_length_limits_are_exact() -> None:
    assert password_policy.problem_with("a1b2c3d4e5f") is not None  # 11
    assert password_policy.problem_with("a1b2c3d4e5f6") is None  # 12
    assert password_policy.problem_with("ab" * 100 + "c") is not None  # 201
    assert password_policy.problem_with("abcde" * 40) is None  # 200


@pytest.mark.parametrize(
    "password",
    [
        "password1234",
        "Password123!",
        "P@ssw0rd2024!",
        "Welcome2024!!",
        "letmein-letmein",
        "ADMINISTRATOR",
        "iloveyou12345",
        "Changeme!2024",
        "qwertyuiop123",
    ],
)
def test_common_words_are_refused_even_when_dressed_up(password: str) -> None:
    assert "common" in (password_policy.problem_with(password) or "")


@pytest.mark.parametrize(
    "password",
    ["qwertyuiopas", "1234567890123", "abcdefghijklm", "mnbvcxzlkjhg", "98765432109876"],
)
def test_keyboard_and_number_runs_are_refused(password: str) -> None:
    assert "sequence" in (password_policy.problem_with(password) or "")


@pytest.mark.parametrize("password", ["aaaaaaaaaaaa", "abababababab", "121212121212"])
def test_a_password_with_almost_no_variety_is_refused(password: str) -> None:
    assert "repeats" in (password_policy.problem_with(password) or "")


def test_five_different_characters_is_enough_variety_and_four_is_not() -> None:
    assert "repeats" in (password_policy.problem_with("abcdabcdabcd") or "")
    assert password_policy.problem_with("abcdeabcdeab") is None


def test_the_persons_own_name_or_email_is_refused() -> None:
    assert "name or email" in (
        password_policy.problem_with("zebra-ada.lovelace-moon", email="ada.lovelace@example.com")
        or ""
    )
    assert "name or email" in (
        password_policy.problem_with("my-lovelace-secret-9", name="Ada Lovelace") or ""
    )


def test_short_parts_of_a_name_do_not_trigger_the_rule() -> None:
    # "Al" and "Bo" are too short to mean anything inside a longer password.
    assert password_policy.problem_with("balloon-bobsled-47", name="Al Bo") is None
    assert password_policy.problem_with("balloon-bobsled-47", email="al@example.com") is None
    # ...while a part of four characters does count.
    assert password_policy.problem_with("balloon-bobsled-47", name="Ada Ballo") is not None


def test_require_raises_with_the_reason() -> None:
    with pytest.raises(ValidationError, match="at least 12"):
        password_policy.require("short")
    password_policy.require("tangerine-lantern-47")
