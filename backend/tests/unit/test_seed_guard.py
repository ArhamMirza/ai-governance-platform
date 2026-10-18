import sys
from types import SimpleNamespace

import pytest

from app import seed


class FakeDb:
    closed = False

    def close(self) -> None:
        self.closed = True


def patch(monkeypatch: pytest.MonkeyPatch, *, real: bool, argv: list[str]):
    ran: list[FakeDb] = []
    db = FakeDb()
    monkeypatch.setattr(
        "app.core.config.get_settings", lambda: SimpleNamespace(is_real_deployment=real)
    )
    monkeypatch.setattr(seed, "SessionLocal", lambda: db)
    monkeypatch.setattr(seed, "seed", lambda session: ran.append(session))
    monkeypatch.setattr(sys, "argv", ["seed", *argv])
    return ran, db


def test_demo_data_is_not_loaded_into_a_real_deployment(monkeypatch: pytest.MonkeyPatch) -> None:
    ran, _ = patch(monkeypatch, real=True, argv=[])

    with pytest.raises(SystemExit) as stopped:
        seed.main()

    assert "Refusing to load demo data" in str(stopped.value)
    assert "--allow-production" in str(stopped.value)
    assert ran == []


def test_it_can_be_overridden_on_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    ran, db = patch(monkeypatch, real=True, argv=["--allow-production"])

    seed.main()

    assert ran == [db] and db.closed


def test_development_just_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    ran, db = patch(monkeypatch, real=False, argv=[])

    seed.main()

    assert ran == [db] and db.closed
