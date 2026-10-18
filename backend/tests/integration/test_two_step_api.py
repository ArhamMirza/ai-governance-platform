"""Two-step sign-in through the real cookie flow: setting up an authenticator,
the two-stage sign-in, recovery codes, turning it off, an administrator
resetting it, and the organization rule for administrators."""

from collections.abc import Callable
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import mfa_ticket, recovery_codes, totp
from app.core.security import hash_password
from app.models.audit_log import AuditLogEntry
from app.models.mfa import MFARecoveryCode, UserMFA
from app.models.session import Session as SessionRow
from app.models.user import User, UserRole
from app.services import mfa_service

API = "/api/v1"
ADA_EMAIL = "ada@example.com"
ADA_PASSWORD = "tangerine-lantern-47"
BOB_EMAIL = "bob@example.com"
BOB_PASSWORD = "violet-harbour-lanterns-31"


class Clock:
    """The time the server sees, which tests move forward a step at a time so
    a code is never reused by accident."""

    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def time(self) -> float:
        return self.now

    def tick(self, steps: int = 1) -> None:
        self.now += totp.STEP_SECONDS * steps

    def code(self, secret: str) -> str:
        return totp.code_for_step(secret, totp.step_at(self.now))


@pytest.fixture()
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(mfa_service, "time", SimpleNamespace(time=fake.time))
    return fake


def browser() -> TestClient:
    from app.main import app

    return TestClient(app)


def sign_in(client: TestClient, email: str, password: str):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def two_step(client: TestClient, ticket: str, code: str):
    return client.post(f"{API}/auth/login/two-step", json={"ticket": ticket, "code": code})


@pytest.fixture()
def admin(unauthenticated_client: TestClient) -> TestClient:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada Admin", "email": ADA_EMAIL, "password": ADA_PASSWORD},
    )
    assert response.status_code == 201
    return unauthenticated_client


def enroll(client: TestClient, clock: Clock) -> tuple[str, list[str]]:
    """Turns two-step sign-in on for whoever the client is signed in as."""
    secret = client.post(f"{API}/auth/two-step/setup").json()["secret"]
    confirmed = client.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(secret)})
    assert confirmed.status_code == 200, confirmed.text
    clock.tick()
    return secret, confirmed.json()["recovery_codes"]


def person(admin: TestClient, role: str = "contributor") -> dict:
    created = admin.post(
        f"{API}/users",
        json={
            "name": "Bob Builder",
            "email": BOB_EMAIL,
            "password": "temporary-passphrase-1",
            "role": role,
        },
    )
    assert created.status_code == 201, created.text
    bob = browser()
    sign_in(bob, BOB_EMAIL, "temporary-passphrase-1")
    changed = bob.post(
        f"{API}/auth/change-password",
        json={"current_password": "temporary-passphrase-1", "new_password": BOB_PASSWORD},
    )
    assert changed.status_code == 200, changed.text
    return {"id": created.json()["id"], "client": bob}


def audit(db: Session, user_id: int, action: str) -> list[AuditLogEntry]:
    return (
        db.query(AuditLogEntry)
        .filter_by(entity_type="User", entity_id=user_id, action=action)
        .order_by(AuditLogEntry.id)
        .all()
    )


def me(client: TestClient) -> dict:
    return client.get(f"{API}/auth/me").json()


# ---------- setting it up ----------


def test_it_is_off_until_set_up(admin: TestClient) -> None:
    assert admin.get(f"{API}/auth/two-step").json() == {
        "enabled": False,
        "recovery_codes_remaining": 0,
        "setup_required": False,
    }
    assert me(admin)["mfa_enabled"] is False


def test_starting_setup_gives_a_key_and_a_link_but_changes_nothing_yet(
    admin: TestClient, db_session: Session
) -> None:
    setup = admin.post(f"{API}/auth/two-step/setup").json()

    assert len(setup["secret"]) == 32
    assert setup["otpauth_uri"].startswith(
        "otpauth://totp/AI%20Governance%20Platform:ada%40example.com"
    )
    assert f"secret={setup['secret']}" in setup["otpauth_uri"]
    assert me(admin)["mfa_enabled"] is False
    # And a fresh sign-in still needs only the password.
    assert "mfa_required" not in sign_in(browser(), ADA_EMAIL, ADA_PASSWORD).json()


def test_the_secret_is_not_stored_readably(admin: TestClient, db_session: Session) -> None:
    secret = admin.post(f"{API}/auth/two-step/setup").json()["secret"]

    stored = db_session.query(UserMFA).one().secret_encrypted

    assert secret not in stored and stored != secret


def test_a_wrong_code_does_not_turn_it_on(admin: TestClient, clock: Clock) -> None:
    secret = admin.post(f"{API}/auth/two-step/setup").json()["secret"]
    wrong = str((int(clock.code(secret)) + 1) % 10**6).zfill(6)

    response = admin.post(f"{API}/auth/two-step/confirm", json={"code": wrong})

    assert response.status_code == 400
    assert "isn't right" in response.json()["detail"]
    assert me(admin)["mfa_enabled"] is False


def test_the_right_code_turns_it_on_and_returns_ten_recovery_codes_once(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret = admin.post(f"{API}/auth/two-step/setup").json()["secret"]

    response = admin.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(secret)})

    codes = response.json()["recovery_codes"]
    assert response.status_code == 200 and len(codes) == len(set(codes)) == 10
    assert me(admin)["mfa_enabled"] is True
    assert admin.get(f"{API}/auth/two-step").json()["recovery_codes_remaining"] == 10
    # Only hashes are kept.
    stored = {row.code_hash for row in db_session.query(MFARecoveryCode)}
    assert stored == {recovery_codes.hash_code(c) for c in codes}
    assert not any(recovery_codes.normalize(c) in h for c in codes for h in stored)
    # They are not shown again.
    assert "recovery_codes" not in admin.get(f"{API}/auth/two-step").json()


def test_setting_up_twice_is_refused_while_it_is_on(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)

    assert admin.post(f"{API}/auth/two-step/setup").status_code == 409


def test_confirming_again_once_it_is_on_is_refused_and_changes_nothing(
    admin: TestClient, clock: Clock
) -> None:
    secret, codes = enroll(admin, clock)

    again = admin.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(secret)})

    assert again.status_code == 400 and "Start the set-up first" in again.json()["detail"]
    # The recovery codes from the first time are still the live ones.
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(other, ticket, codes[0]).status_code == 200


def test_guessing_codes_while_setting_up_is_limited(admin: TestClient, clock: Clock) -> None:
    secret = admin.post(f"{API}/auth/two-step/setup").json()["secret"]

    for _ in range(5):
        wrong = admin.post(f"{API}/auth/two-step/confirm", json={"code": wrong_code(clock, secret)})
        assert wrong.status_code == 400

    locked = admin.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(secret)})

    assert locked.status_code == 429
    assert me(admin)["mfa_enabled"] is False


def test_confirming_without_starting_is_refused(admin: TestClient, clock: Clock) -> None:
    assert admin.post(f"{API}/auth/two-step/confirm", json={"code": "123456"}).status_code == 400


def test_starting_again_replaces_the_unfinished_secret(admin: TestClient, clock: Clock) -> None:
    first = admin.post(f"{API}/auth/two-step/setup").json()["secret"]
    second = admin.post(f"{API}/auth/two-step/setup").json()["secret"]

    assert first != second
    stale = admin.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(first)})
    assert stale.status_code == 400
    fresh = admin.post(f"{API}/auth/two-step/confirm", json={"code": clock.code(second)})
    assert fresh.status_code == 200


def test_setup_needs_a_session(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.post(f"{API}/auth/two-step/setup").status_code == 401
    assert unauthenticated_client.get(f"{API}/auth/two-step").status_code == 401


def test_turning_it_on_is_recorded(admin: TestClient, clock: Clock, db_session: Session) -> None:
    enroll(admin, clock)

    [entry] = audit(db_session, me(admin)["id"], "mfa_enabled")
    assert entry.actor_id == me(admin)["id"]


# ---------- signing in with it ----------


def test_a_correct_password_alone_gets_no_session(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)
    other = browser()

    response = sign_in(other, ADA_EMAIL, ADA_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["mfa_required"] is True and body["ticket"]
    assert "set-cookie" not in response.headers
    assert other.get(f"{API}/auth/me").status_code == 401
    assert other.get(f"{API}/policies").status_code == 401


def test_the_ticket_and_a_current_code_sign_you_in(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    response = two_step(other, ticket, clock.code(secret))

    assert response.status_code == 200
    assert response.json()["email"] == ADA_EMAIL and response.json()["mfa_enabled"] is True
    assert other.get(f"{API}/policies").status_code == 200
    [login] = audit(db_session, me(admin)["id"], "login")
    assert login.diff == {"ip": "testclient", "second_factor": "totp"}


def test_an_account_without_it_signs_in_as_before(admin: TestClient, clock: Clock) -> None:
    person(admin)
    other = browser()

    response = sign_in(other, BOB_EMAIL, BOB_PASSWORD)

    assert "mfa_required" not in response.json() and response.json()["email"] == BOB_EMAIL
    assert other.get(f"{API}/policies").status_code == 200


def test_a_wrong_code_is_refused_and_recorded(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    wrong = str((int(clock.code(secret)) + 1) % 10**6).zfill(6)

    response = two_step(other, ticket, wrong)

    assert response.status_code == 401 and "isn't right" in response.json()["detail"]
    assert other.get(f"{API}/policies").status_code == 401
    [failed] = audit(db_session, me(admin)["id"], "mfa_failed")
    assert (failed.actor_id, failed.diff) == (None, {"ip": "testclient"})
    assert audit(db_session, me(admin)["id"], "login") == []


def test_a_code_works_only_once(admin: TestClient, clock: Clock) -> None:
    secret, _ = enroll(admin, clock)
    code = clock.code(secret)
    first = browser()
    second = browser()

    assert (
        two_step(first, sign_in(first, ADA_EMAIL, ADA_PASSWORD).json()["ticket"], code).status_code
        == 200
    )
    replay = two_step(second, sign_in(second, ADA_EMAIL, ADA_PASSWORD).json()["ticket"], code)

    assert replay.status_code == 401
    # The next code is fine.
    clock.tick()
    ticket = sign_in(second, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(second, ticket, clock.code(secret)).status_code == 200


def test_the_code_for_the_next_step_is_tolerated_but_one_already_used_is_not(
    admin: TestClient, clock: Clock
) -> None:
    secret, _ = enroll(admin, clock)
    used_at_setup = totp.code_for_step(secret, totp.step_at(clock.now) - 1)
    next_step = totp.code_for_step(secret, totp.step_at(clock.now) + 1)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    assert two_step(other, ticket, used_at_setup).status_code == 401
    assert two_step(other, ticket, next_step).status_code == 200


def test_a_ticket_cannot_be_used_with_someone_elses_code(admin: TestClient, clock: Clock) -> None:
    ada_secret, _ = enroll(admin, clock)
    bob = person(admin)
    bob_secret, _ = enroll(bob["client"], clock)
    other = browser()
    ada_ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    response = two_step(other, ada_ticket, clock.code(bob_secret))

    assert response.status_code == 401
    assert ada_secret != bob_secret


@pytest.mark.parametrize("tamper", ["garbage", "", "a.b", "x" * 600])
def test_a_made_up_ticket_is_refused(admin: TestClient, clock: Clock, tamper: str) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()

    response = two_step(other, tamper or "-", clock.code(secret))

    assert response.status_code in (401, 422)
    assert other.get(f"{API}/policies").status_code == 401


def test_an_expired_ticket_is_refused(
    admin: TestClient, clock: Clock, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    real = mfa_ticket.time.time
    later = SimpleNamespace(time=lambda: real() + mfa_ticket.TTL_SECONDS + 1)
    monkeypatch.setattr(mfa_ticket, "time", later)

    response = two_step(other, ticket, clock.code(secret))

    assert response.status_code == 401 and "took too long" in response.json()["detail"]


def test_changing_the_password_between_the_steps_voids_the_ticket(
    admin: TestClient, clock: Clock
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    admin.post(
        f"{API}/auth/change-password",
        json={"current_password": ADA_PASSWORD, "new_password": "a-fresh-passphrase-88"},
    )

    assert two_step(other, ticket, clock.code(secret)).status_code == 401


def test_a_ticket_for_an_account_that_has_since_turned_it_off_is_refused(
    admin: TestClient, clock: Clock
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": clock.code(secret)}
    )
    clock.tick()

    response = two_step(other, ticket, clock.code(secret))

    assert response.status_code == 401
    # Told to start again, rather than that the code was wrong.
    assert "took too long" in response.json()["detail"]


def test_a_deactivated_account_cannot_finish_signing_in(admin: TestClient, clock: Clock) -> None:
    bob = person(admin)
    secret, _ = enroll(bob["client"], clock)
    other = browser()
    ticket = sign_in(other, BOB_EMAIL, BOB_PASSWORD).json()["ticket"]
    admin.patch(f"{API}/users/{bob['id']}", json={"is_active": False})

    assert two_step(other, ticket, clock.code(secret)).status_code == 401


# ---------- guessing codes ----------


def wrong_code(clock: Clock, secret: str) -> str:
    return str((int(clock.code(secret)) + 1) % 10**6).zfill(6)


def test_five_wrong_codes_lock_the_codes_even_for_the_right_one(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    for _ in range(5):
        assert two_step(other, ticket, wrong_code(clock, secret)).status_code == 401

    assert two_step(other, ticket, wrong_code(clock, secret)).status_code == 429
    assert two_step(other, ticket, clock.code(secret)).status_code == 429
    assert len(audit(db_session, me(admin)["id"], "mfa_failed")) == 5
    assert len(audit(db_session, me(admin)["id"], "mfa_locked")) == 1


def test_signing_in_again_with_the_password_does_not_give_fresh_guesses(
    admin: TestClient, clock: Clock
) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    for _ in range(5):
        ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
        two_step(other, ticket, wrong_code(clock, secret))

    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(other, ticket, clock.code(secret)).status_code == 429


def test_one_accounts_wrong_codes_do_not_lock_another(admin: TestClient, clock: Clock) -> None:
    ada_secret, _ = enroll(admin, clock)
    bob = person(admin)
    bob_secret, _ = enroll(bob["client"], clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    for _ in range(5):
        two_step(other, ticket, wrong_code(clock, ada_secret))
    third = browser()

    ticket = sign_in(third, BOB_EMAIL, BOB_PASSWORD).json()["ticket"]

    assert two_step(third, ticket, clock.code(bob_secret)).status_code == 200


def test_a_right_code_clears_the_count(admin: TestClient, clock: Clock) -> None:
    secret, _ = enroll(admin, clock)
    other = browser()
    for _ in range(4):
        ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
        two_step(other, ticket, wrong_code(clock, secret))
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(other, ticket, clock.code(secret)).status_code == 200
    clock.tick()

    for _ in range(4):
        ticket = sign_in(browser(), ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
        assert two_step(browser(), ticket, wrong_code(clock, secret)).status_code == 401
    ticket = sign_in(browser(), ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(browser(), ticket, clock.code(secret)).status_code == 200


def test_one_address_guessing_codes_is_slowed_as_well(admin: TestClient, clock: Clock) -> None:
    from app.services import auth_service

    secret, _ = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    for _ in range(19):
        auth_service._login_attempts_by_address.record_failure("testclient")

    first = two_step(other, ticket, wrong_code(clock, secret))
    blocked = two_step(other, ticket, clock.code(secret))

    assert first.status_code == 401
    assert blocked.status_code == 429 and "this address" in blocked.json()["detail"]


# ---------- recovery codes ----------


def test_a_recovery_code_signs_you_in_once(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    _, codes = enroll(admin, clock)
    first = browser()
    second = browser()

    ok = two_step(first, sign_in(first, ADA_EMAIL, ADA_PASSWORD).json()["ticket"], codes[0])
    again = two_step(second, sign_in(second, ADA_EMAIL, ADA_PASSWORD).json()["ticket"], codes[0])

    assert ok.status_code == 200 and again.status_code == 401
    assert first.get(f"{API}/policies").status_code == 200
    assert admin.get(f"{API}/auth/two-step").json()["recovery_codes_remaining"] == 9
    [used] = audit(db_session, me(admin)["id"], "mfa_recovery_used")
    assert used.diff == {"ip": "testclient", "remaining": 9}
    assert codes[0] not in str(used.diff)
    assert audit(db_session, me(admin)["id"], "login")[-1].diff["second_factor"] == "recovery"


def test_a_recovery_code_can_be_typed_loosely(admin: TestClient, clock: Clock) -> None:
    _, codes = enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    response = two_step(other, ticket, codes[1].replace("-", "").lower())

    assert response.status_code == 200


def test_a_wrong_recovery_code_counts_as_a_wrong_code(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    for _ in range(5):
        assert two_step(other, ticket, "AAAAA-AAAAA").status_code == 401

    assert two_step(other, ticket, "AAAAA-AAAAA").status_code == 429


def test_one_persons_recovery_code_does_not_work_for_another(
    admin: TestClient, clock: Clock
) -> None:
    _, ada_codes = enroll(admin, clock)
    bob = person(admin)
    enroll(bob["client"], clock)
    other = browser()
    ticket = sign_in(other, BOB_EMAIL, BOB_PASSWORD).json()["ticket"]

    assert two_step(other, ticket, ada_codes[0]).status_code == 401


def test_new_recovery_codes_replace_the_old_ones(admin: TestClient, clock: Clock) -> None:
    secret, old = enroll(admin, clock)

    response = admin.post(
        f"{API}/auth/two-step/recovery-codes",
        json={"password": ADA_PASSWORD, "code": clock.code(secret)},
    )

    new = response.json()["recovery_codes"]
    assert response.status_code == 200 and len(new) == 10 and not set(new) & set(old)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]
    assert two_step(other, ticket, old[0]).status_code == 401
    assert two_step(other, ticket, new[0]).status_code == 200


def test_new_recovery_codes_need_the_password_and_a_code(admin: TestClient, clock: Clock) -> None:
    secret, _ = enroll(admin, clock)

    bad_password = admin.post(
        f"{API}/auth/two-step/recovery-codes",
        json={"password": "wrong", "code": clock.code(secret)},
    )
    bad_code = admin.post(
        f"{API}/auth/two-step/recovery-codes",
        json={"password": ADA_PASSWORD, "code": wrong_code(clock, secret)},
    )

    assert bad_password.status_code == 401 and "password" in bad_password.json()["detail"]
    assert bad_code.status_code == 401 and "isn't right" in bad_code.json()["detail"]


def test_a_recovery_code_still_works_when_the_secret_can_no_longer_be_read(
    admin: TestClient, clock: Clock, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret, codes = enroll(admin, clock)
    monkeypatch.setattr(mfa_service, "decrypt", lambda value: None)
    other = browser()
    ticket = sign_in(other, ADA_EMAIL, ADA_PASSWORD).json()["ticket"]

    # Fails closed for the authenticator...
    assert two_step(other, ticket, clock.code(secret)).status_code == 401
    # ...but a recovery code gets the person in to reset it.
    assert two_step(other, ticket, codes[0]).status_code == 200


# ---------- turning it off ----------


def test_it_can_be_turned_off_with_the_password_and_a_code(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret, _ = enroll(admin, clock)
    elsewhere = browser()
    two_step(
        elsewhere, sign_in(elsewhere, ADA_EMAIL, ADA_PASSWORD).json()["ticket"], clock.code(secret)
    )
    clock.tick()

    response = admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": clock.code(secret)}
    )

    assert response.status_code == 204
    assert me(admin)["mfa_enabled"] is False
    assert db_session.query(UserMFA).count() == 0 and db_session.query(MFARecoveryCode).count() == 0
    assert "mfa_required" not in sign_in(browser(), ADA_EMAIL, ADA_PASSWORD).json()
    # Every other device is signed out; this one stays.
    assert elsewhere.get(f"{API}/policies").status_code == 401
    assert admin.get(f"{API}/policies").status_code == 200
    assert audit(db_session, me(admin)["id"], "mfa_disabled")


def test_it_cannot_be_turned_off_with_only_one_of_the_two(admin: TestClient, clock: Clock) -> None:
    secret, _ = enroll(admin, clock)

    wrong_password = admin.post(
        f"{API}/auth/two-step/disable", json={"password": "nope", "code": clock.code(secret)}
    )
    wrong_code_ = admin.post(
        f"{API}/auth/two-step/disable",
        json={"password": ADA_PASSWORD, "code": wrong_code(clock, secret)},
    )

    assert wrong_password.status_code == 401 and wrong_code_.status_code == 401
    assert me(admin)["mfa_enabled"] is True


def test_guessing_while_turning_it_off_is_limited(admin: TestClient, clock: Clock) -> None:
    secret, _ = enroll(admin, clock)
    for _ in range(5):
        admin.post(
            f"{API}/auth/two-step/disable",
            json={"password": ADA_PASSWORD, "code": wrong_code(clock, secret)},
        )

    locked = admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": clock.code(secret)}
    )

    assert locked.status_code == 429
    assert me(admin)["mfa_enabled"] is True


def test_turning_off_what_is_not_on_is_refused(admin: TestClient, clock: Clock) -> None:
    response = admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": "123456"}
    )

    assert response.status_code == 409


def test_a_recovery_code_can_authorise_turning_it_off(admin: TestClient, clock: Clock) -> None:
    _, codes = enroll(admin, clock)

    response = admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": codes[0]}
    )

    assert response.status_code == 204


# ---------- an administrator resetting it ----------


def person_other(admin: TestClient) -> int:
    created = admin.post(
        f"{API}/users",
        json={"name": "Carol", "email": "carol@example.com", "password": "temporary-passphrase-2"},
    )
    return created.json()["id"]


def test_another_administrator_can_reset_it(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    bob = person(admin)
    secret, _ = enroll(bob["client"], clock)
    assert bob["client"].get(f"{API}/policies").status_code == 200

    response = admin.post(f"{API}/users/{bob['id']}/reset-two-step")

    assert response.status_code == 200 and response.json()["mfa_enabled"] is False
    assert bob["client"].get(f"{API}/policies").status_code == 401
    assert "mfa_required" not in sign_in(browser(), BOB_EMAIL, BOB_PASSWORD).json()
    [entry] = audit(db_session, bob["id"], "mfa_reset")
    assert (entry.actor_id, entry.diff) == (me(admin)["id"], {"was_on": True})
    assert db_session.query(MFARecoveryCode).filter_by(user_id=bob["id"]).count() == 0


def test_an_administrator_cannot_reset_their_own(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)

    assert admin.post(f"{API}/users/{me(admin)['id']}/reset-two-step").status_code == 409
    assert me(admin)["mfa_enabled"] is True


def test_resetting_an_unknown_account_is_not_found(admin: TestClient) -> None:
    assert admin.post(f"{API}/users/9999/reset-two-step").status_code == 404


def test_only_someone_who_manages_users_can_reset_it(admin: TestClient, clock: Clock) -> None:
    bob = person(admin)
    other = person_other(admin)

    assert bob["client"].post(f"{API}/users/{other}/reset-two-step").status_code == 403
    assert browser().post(f"{API}/users/{other}/reset-two-step").status_code == 401


def test_the_users_list_says_who_has_it(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)
    person(admin)

    listed = {u["email"]: u["mfa_enabled"] for u in admin.get(f"{API}/users").json()}

    assert listed == {ADA_EMAIL: True, BOB_EMAIL: False}


# ---------- the organization rule for administrators ----------


def test_the_rule_starts_off_and_counts_who_it_would_catch(admin: TestClient, clock: Clock) -> None:
    assert admin.get(f"{API}/security/settings").json() == {
        "require_mfa_for_admins": False,
        "admins_without_mfa": 1,
    }
    enroll(admin, clock)
    assert admin.get(f"{API}/security/settings").json()["admins_without_mfa"] == 0


def test_it_cannot_be_required_until_you_have_it_yourself(admin: TestClient, clock: Clock) -> None:
    response = admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    assert response.status_code == 409 and "your own account first" in response.json()["detail"]
    assert admin.get(f"{API}/security/settings").json()["require_mfa_for_admins"] is False


def test_requiring_it_holds_an_administrator_without_it_to_the_setup_screen(
    admin: TestClient, clock: Clock
) -> None:
    enroll(admin, clock)
    second = person(admin, role="admin")
    second_client = second["client"]
    assert second_client.get(f"{API}/policies").status_code == 200

    on = admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    assert on.json() == {"require_mfa_for_admins": True, "admins_without_mfa": 1}
    blocked = second_client.get(f"{API}/policies")
    assert blocked.status_code == 403 and "two-step sign-in" in blocked.json()["detail"]
    assert me(second_client)["mfa_setup_required"] is True
    assert second_client.get(f"{API}/auth/two-step").json()["setup_required"] is True
    # The set-up routes stay open to them...
    secret, _ = enroll(second_client, clock)
    # ...and once it's on, they are through.
    assert second_client.get(f"{API}/policies").status_code == 200
    assert me(second_client)["mfa_setup_required"] is False
    assert secret


def test_the_rule_does_not_touch_other_roles(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)
    contributor = person(admin)
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    assert contributor["client"].get(f"{API}/policies").status_code == 200
    assert me(contributor["client"])["mfa_setup_required"] is False


def test_an_employee_login_is_not_held_by_the_rule(admin: TestClient, clock: Clock) -> None:
    enroll(admin, clock)
    admin.post(
        f"{API}/users",
        json={
            "name": "Elena",
            "email": "elena@example.com",
            "password": "temporary-passphrase-3",
            "role": "employee",
        },
    )
    elena = browser()
    sign_in(elena, "elena@example.com", "temporary-passphrase-3")
    elena.post(
        f"{API}/auth/change-password",
        json={
            "current_password": "temporary-passphrase-3",
            "new_password": "violet-harbour-lanterns-77",
        },
    )
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    assert elena.get(f"{API}/staff/ai-use-notice").status_code == 200


def test_while_required_an_administrator_cannot_turn_it_off(
    admin: TestClient, clock: Clock
) -> None:
    secret, _ = enroll(admin, clock)
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    response = admin.post(
        f"{API}/auth/two-step/disable", json={"password": ADA_PASSWORD, "code": clock.code(secret)}
    )

    assert response.status_code == 409 and "requires" in response.json()["detail"]
    assert me(admin)["mfa_enabled"] is True


def test_a_required_administrator_whose_two_step_is_reset_must_set_it_up_again(
    admin: TestClient, clock: Clock
) -> None:
    enroll(admin, clock)
    second = person(admin, role="admin")
    enroll(second["client"], clock)
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})

    admin.post(f"{API}/users/{second['id']}/reset-two-step")
    again = browser()
    sign_in(again, BOB_EMAIL, BOB_PASSWORD)

    assert again.get(f"{API}/policies").status_code == 403
    assert me(again)["mfa_setup_required"] is True


def test_the_rule_can_be_turned_off_again_and_changes_are_recorded(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    enroll(admin, clock)
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})
    admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": True})  # no change
    off = admin.put(f"{API}/security/settings", json={"require_mfa_for_admins": False})

    assert off.json()["require_mfa_for_admins"] is False
    entries = (
        db_session.query(AuditLogEntry)
        .filter_by(entity_type="SecuritySettings", action="updated")
        .order_by(AuditLogEntry.id)
        .all()
    )
    assert [e.diff for e in entries] == [
        {"require_mfa_for_admins": True},
        {"require_mfa_for_admins": False},
    ]


def test_only_someone_who_manages_settings_can_see_or_change_the_rule(
    admin: TestClient, clock: Clock
) -> None:
    bob = person(admin)

    assert bob["client"].get(f"{API}/security/settings").status_code == 403
    assert (
        bob["client"]
        .put(f"{API}/security/settings", json={"require_mfa_for_admins": True})
        .status_code
        == 403
    )
    assert browser().get(f"{API}/security/settings").status_code == 401


def test_an_unknown_field_in_the_settings_update_is_refused(
    admin: TestClient, clock: Clock
) -> None:
    enroll(admin, clock)

    response = admin.put(
        f"{API}/security/settings", json={"require_mfa_for_admins": True, "extra": 1}
    )

    assert response.status_code == 422


# ---------- sessions and the existing flows ----------


def test_a_session_from_before_it_was_turned_on_keeps_working(
    admin: TestClient, clock: Clock
) -> None:
    other = browser()
    sign_in(other, ADA_EMAIL, ADA_PASSWORD)

    enroll(admin, clock)

    assert other.get(f"{API}/policies").status_code == 200


def test_the_two_step_route_checks_the_origin_like_the_rest(
    admin: TestClient, clock: Clock
) -> None:
    response = admin.post(f"{API}/auth/two-step/setup", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403


def test_a_password_reset_leaves_two_step_on(admin: TestClient, clock: Clock) -> None:
    bob = person(admin)
    secret, _ = enroll(bob["client"], clock)

    temporary = admin.post(f"{API}/users/{bob['id']}/reset-password").json()["temporary_password"]
    other = browser()
    body = sign_in(other, BOB_EMAIL, temporary).json()

    assert body["mfa_required"] is True
    assert (
        two_step(other, body["ticket"], clock.code(secret)).json()["must_change_password"] is True
    )


def test_rows_for_sessions_are_not_created_until_the_code_is_given(
    admin: TestClient, clock: Clock, db_session: Session
) -> None:
    secret, _ = enroll(admin, clock)
    before = db_session.query(SessionRow).count()

    sign_in(browser(), ADA_EMAIL, ADA_PASSWORD)

    assert db_session.query(SessionRow).count() == before


def test_legacy_users_are_unaffected(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user(
        email="old@example.com", password_hash=hash_password(ADA_PASSWORD), role=UserRole.VIEWER
    )

    response = sign_in(unauthenticated_client, "old@example.com", ADA_PASSWORD)

    assert response.status_code == 200 and response.json()["mfa_enabled"] is False
