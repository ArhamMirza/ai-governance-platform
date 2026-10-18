import re

import pytest

from app.core import recovery_codes


def test_ten_distinct_codes_are_made_in_the_expected_shape() -> None:
    codes = recovery_codes.generate()

    assert len(codes) == recovery_codes.COUNT == 10
    assert len(set(codes)) == 10
    for code in codes:
        assert re.fullmatch(r"[A-Z2-9]{5}-[A-Z2-9]{5}", code)


def test_no_look_alike_characters_are_used() -> None:
    joined = "".join("".join(recovery_codes.generate()) for _ in range(30))

    assert not set(joined) & set("01OIL")


def test_typing_it_any_way_gives_the_same_code() -> None:
    code = "ABCDE-FGHJK"

    for typed in ("abcde-fghjk", "ABCDEFGHJK", " abcde fghjk ", "abcde-fghjk\n"):
        assert recovery_codes.normalize(typed) == "ABCDEFGHJK"
        assert recovery_codes.hash_code(typed) == recovery_codes.hash_code(code)


def test_different_codes_hash_differently_and_the_hash_hides_the_code() -> None:
    first, second = recovery_codes.generate()[:2]

    assert recovery_codes.hash_code(first) != recovery_codes.hash_code(second)
    assert re.fullmatch(r"[0-9a-f]{64}", recovery_codes.hash_code(first))
    assert recovery_codes.normalize(first) not in recovery_codes.hash_code(first)


@pytest.mark.parametrize("code", ["ABCDE-FGHJK", "abcdefghjk", "A2345-6789A"])
def test_things_that_look_like_a_recovery_code(code: str) -> None:
    assert recovery_codes.looks_like_one(code) is True


@pytest.mark.parametrize(
    "code",
    ["", "123456", "ABCDE-FGHJ", "ABCDE-FGHJKM", "ABCDE-FGHJ0", "ABCDE-FGHJI", "ABCDE-FGHJ!"],
)
def test_and_things_that_do_not(code: str) -> None:
    assert recovery_codes.looks_like_one(code) is False


def test_an_authenticator_code_is_never_mistaken_for_a_recovery_code() -> None:
    assert recovery_codes.looks_like_one("123456") is False
    assert recovery_codes.looks_like_one("000000") is False
