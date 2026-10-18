import logging
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core import setup_code
from app.core.security import hash_password
from app.models.user import User


def configure(monkeypatch: pytest.MonkeyPatch, *, real: bool, code: str | None) -> None:
    fake = SimpleNamespace(is_real_deployment=real, setup_code=code)
    monkeypatch.setattr(setup_code, "get_settings", lambda: fake)
    monkeypatch.setattr(setup_code, "_generated", None)


def test_a_configured_code_is_the_one_expected(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, real=True, code="  my-own-code  ")

    assert setup_code.expected() == "my-own-code"
    assert setup_code.matches("my-own-code") is True
    assert setup_code.matches("  my-own-code ") is True


@pytest.mark.parametrize(
    "candidate", [None, "", "   ", "my-own-cod", "my-own-codex", "MY-OWN-CODE"]
)
def test_anything_else_does_not_match(monkeypatch: pytest.MonkeyPatch, candidate) -> None:
    configure(monkeypatch, real=True, code="my-own-code")

    assert setup_code.matches(candidate) is False


def test_without_a_configured_code_one_is_made_and_kept_for_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure(monkeypatch, real=True, code=None)

    first = setup_code.expected()
    second = setup_code.expected()

    assert first == second
    assert len(first) >= 12
    assert setup_code.matches(first) is True


def test_a_blank_configured_code_counts_as_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, real=True, code="   ")

    assert setup_code.expected() != "   "
    assert setup_code.matches("") is False


def test_a_new_run_makes_a_different_code(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, real=True, code=None)
    first = setup_code.expected()
    monkeypatch.setattr(setup_code, "_generated", None)

    assert setup_code.expected() != first


def test_only_a_real_deployment_requires_it(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, real=False, code=None)
    assert setup_code.required() is False
    configure(monkeypatch, real=True, code=None)
    assert setup_code.required() is True


# ---------- the startup message ----------


def test_the_generated_code_is_printed_when_an_account_is_still_to_be_made(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    configure(monkeypatch, real=True, code=None)

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        setup_code.announce(db_session)

    assert setup_code.expected() in caplog.text
    assert "setup code" in caplog.text


def test_a_configured_code_is_never_echoed_into_the_log(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    configure(monkeypatch, real=True, code="my-own-secret-code")

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        setup_code.announce(db_session)

    assert "SETUP_CODE" in caplog.text
    assert "my-own-secret-code" not in caplog.text


def test_nothing_is_printed_in_development(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    configure(monkeypatch, real=False, code=None)

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        setup_code.announce(db_session)

    assert caplog.text == ""


def test_nothing_is_printed_once_an_account_exists(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    configure(monkeypatch, real=True, code=None)
    db_session.add(User(name="A", email="a@example.com", password_hash=hash_password("x" * 14)))
    db_session.commit()

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        setup_code.announce(db_session)

    assert caplog.text == ""
