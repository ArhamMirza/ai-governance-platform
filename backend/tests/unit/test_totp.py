import base64
import re

import pytest

from app.core import totp

# RFC 6238, appendix B: the SHA-1 secret is the ASCII string "12345678901234567890".
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
# (time, 8-digit code from the RFC). The last six digits are the 6-digit code.
RFC_VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


@pytest.mark.parametrize(("timestamp", "expected"), RFC_VECTORS)
def test_it_matches_the_rfc_6238_test_vectors(timestamp: int, expected: str) -> None:
    assert totp.code_for_step(RFC_SECRET, totp.step_at(timestamp)) == expected[-6:]


def test_a_step_is_thirty_seconds() -> None:
    assert totp.step_at(0) == 0
    assert totp.step_at(29.999) == 0
    assert totp.step_at(30) == 1
    assert totp.step_at(59) == 1
    assert totp.step_at(60) == 2


def test_a_code_is_six_digits_with_leading_zeros_kept() -> None:
    code = totp.code_for_step(RFC_SECRET, totp.step_at(1111111109))

    assert code == "081804"
    assert len(code) == 6


# ---------- checking a code ----------

NOW = 1_700_000_000.0
STEP = totp.step_at(NOW)


def code(step: int) -> str:
    return totp.code_for_step(RFC_SECRET, step)


def test_the_current_code_is_accepted_and_reports_its_step() -> None:
    assert totp.verify(RFC_SECRET, code(STEP), now=NOW) == STEP


@pytest.mark.parametrize("offset", [-1, 1])
def test_one_step_either_side_is_tolerated_for_clock_drift(offset: int) -> None:
    assert totp.verify(RFC_SECRET, code(STEP + offset), now=NOW) == STEP + offset


@pytest.mark.parametrize("offset", [-2, 2, -10, 10])
def test_further_away_than_that_is_refused(offset: int) -> None:
    assert totp.verify(RFC_SECRET, code(STEP + offset), now=NOW) is None


def test_the_edge_of_a_step_moves_the_window() -> None:
    just_before = (STEP + 1) * totp.STEP_SECONDS - 0.001
    just_after = (STEP + 1) * totp.STEP_SECONDS

    assert totp.verify(RFC_SECRET, code(STEP - 1), now=just_before) == STEP - 1
    assert totp.verify(RFC_SECRET, code(STEP - 1), now=just_after) is None


def test_a_code_cannot_be_used_twice_or_after_a_later_one() -> None:
    first = totp.verify(RFC_SECRET, code(STEP), now=NOW)
    assert first == STEP

    assert totp.verify(RFC_SECRET, code(STEP), now=NOW, after_step=first) is None
    # An earlier code than the last one used is refused too, even in the window.
    assert totp.verify(RFC_SECRET, code(STEP - 1), now=NOW, after_step=first) is None
    # The next one is fine.
    assert totp.verify(RFC_SECRET, code(STEP + 1), now=NOW, after_step=first) == STEP + 1


def test_after_step_none_means_nothing_has_been_used_yet() -> None:
    assert totp.verify(RFC_SECRET, code(STEP - 1), now=NOW, after_step=None) == STEP - 1


def test_a_code_for_another_secret_is_refused() -> None:
    other = totp.new_secret()

    assert totp.verify(RFC_SECRET, totp.code_for_step(other, STEP), now=NOW) is None


@pytest.mark.parametrize(
    "bad",
    ["", "12345", "1234567", "abcdef", "12 345", "٠٠٠٠٠٠", "１２３４５６", "123456\n", "-12345"],
)
def test_anything_that_is_not_six_ascii_digits_is_refused(bad: str) -> None:
    assert totp.verify(RFC_SECRET, bad, now=NOW) is None


def test_spaces_and_dashes_in_a_typed_code_are_ignored() -> None:
    typed = code(STEP)

    assert totp.verify(RFC_SECRET, f"{typed[:3]} {typed[3:]}", now=NOW) == STEP
    assert totp.verify(RFC_SECRET, f"{typed[:3]}-{typed[3:]}", now=NOW) == STEP
    assert totp.verify(RFC_SECRET, f" {typed} ", now=NOW) == STEP


# ---------- the secret and the link ----------


def test_a_new_secret_is_160_bits_of_base32_and_never_repeats() -> None:
    secrets_made = {totp.new_secret() for _ in range(50)}

    assert len(secrets_made) == 50
    for secret in secrets_made:
        assert re.fullmatch(r"[A-Z2-7]{32}", secret)
        assert len(base64.b32decode(secret)) == 20


def test_the_secret_can_be_typed_in_lowercase_or_with_spaces() -> None:
    spaced = " ".join(RFC_SECRET[i : i + 4] for i in range(0, len(RFC_SECRET), 4)).lower()

    assert totp.code_for_step(spaced, STEP) == code(STEP)


def test_the_provisioning_link_has_what_an_authenticator_app_needs() -> None:
    uri = totp.provisioning_uri("ABCDEFGH", "ada+test@example.com")

    assert uri.startswith("otpauth://totp/AI%20Governance%20Platform:ada%2Btest%40example.com?")
    for part in ("secret=ABCDEFGH", "issuer=AI%20Governance%20Platform", "algorithm=SHA1"):
        assert part in uri
    assert "digits=6" in uri and "period=30" in uri
