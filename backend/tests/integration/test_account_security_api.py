"""Password rules, changing and resetting passwords, ending sessions, and the
audit trail of sign-ins. All through the real cookie flow: the login_as
override replaces the session check these tests exist to exercise."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.audit_log import AuditLogEntry
from app.models.password_history import PasswordHistory
from app.models.session import Session as SessionRow
from app.models.user import User, UserRole

API = "/api/v1"
ADA_PASSWORD = "tangerine-lantern-47"
NEW_PASSWORD = "a-much-better-passphrase"


def browser() -> TestClient:
    """A separate browser: its own cookie jar, same app and database."""
    from app.main import app

    return TestClient(app)


def sign_in(client: TestClient, email: str, password: str):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


@pytest.fixture()
def admin(unauthenticated_client: TestClient) -> TestClient:
    """Registered and signed in as the first account."""
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada Admin", "email": "ada@example.com", "password": ADA_PASSWORD},
    )
    assert response.status_code == 201
    return unauthenticated_client


def create_person(
    admin: TestClient, email: str, role: str = "contributor", password: str = ""
) -> dict:
    response = admin.post(
        f"{API}/users",
        json={
            "name": "Bob Builder",
            "email": email,
            "password": password or "temporary-passphrase-1",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def settled_person(admin: TestClient, email: str = "bob@example.com") -> tuple[dict, TestClient]:
    """Someone who has signed in and replaced the temporary password."""
    person = create_person(admin, email)
    bob = browser()
    assert sign_in(bob, email, "temporary-passphrase-1").status_code == 200
    changed = bob.post(
        f"{API}/auth/change-password",
        json={"current_password": "temporary-passphrase-1", "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200, changed.text
    return person, bob


def audit(db: Session, user_id: int, action: str) -> list[AuditLogEntry]:
    return (
        db.query(AuditLogEntry)
        .filter_by(entity_type="User", entity_id=user_id, action=action)
        .order_by(AuditLogEntry.id)
        .all()
    )


# ---------- the rules ----------


def test_registration_refuses_a_weak_password(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "Password123!"},
    )

    assert response.status_code == 400
    assert "common" in response.json()["detail"]
    assert unauthenticated_client.get(f"{API}/auth/registration-status").json() == {
        "registration_open": True,
        "setup_code_required": False,
    }


def test_registration_refuses_a_short_password(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "short-one-1"},
    )

    assert response.status_code == 400
    assert "at least 12" in response.json()["detail"]


def test_a_new_account_is_created_with_a_temporary_password_to_replace(admin: TestClient) -> None:
    person = create_person(admin, "bob@example.com")

    assert person["must_change_password"] is True
    assert admin.get(f"{API}/auth/me").json()["must_change_password"] is False


def test_creating_an_account_applies_the_same_rules(admin: TestClient) -> None:
    response = admin.post(
        f"{API}/users",
        json={"name": "Bob", "email": "bob@example.com", "password": "qwertyuiopas"},
    )

    assert response.status_code == 400


# ---------- until the password is replaced ----------


def test_until_the_password_is_replaced_the_login_reaches_nothing_else(admin: TestClient) -> None:
    create_person(admin, "bob@example.com")
    bob = browser()
    assert sign_in(bob, "bob@example.com", "temporary-passphrase-1").status_code == 200

    assert bob.get(f"{API}/auth/me").status_code == 200
    blocked = bob.get(f"{API}/policies")
    assert blocked.status_code == 403
    assert "choose a new password" in blocked.json()["detail"]
    assert bob.get(f"{API}/staff/ai-tools").status_code == 403
    assert bob.post(f"{API}/auth/logout").status_code == 204


def test_replacing_the_password_opens_the_app(admin: TestClient) -> None:
    _, bob = settled_person(admin)

    assert bob.get(f"{API}/policies").status_code == 200
    assert bob.get(f"{API}/auth/me").json()["must_change_password"] is False


def test_an_old_weak_password_is_flagged_at_sign_in(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    # An account from before the rules, with a password the rules would refuse.
    make_user(email="old@example.com", password_hash=hash_password("password123"))

    assert sign_in(unauthenticated_client, "old@example.com", "password123").status_code == 200

    assert unauthenticated_client.get(f"{API}/policies").status_code == 403
    assert unauthenticated_client.get(f"{API}/auth/me").json()["must_change_password"] is True


def test_a_good_old_password_is_not_flagged(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user(email="good@example.com", password_hash=hash_password(ADA_PASSWORD))

    sign_in(unauthenticated_client, "good@example.com", ADA_PASSWORD)

    assert unauthenticated_client.get(f"{API}/policies").status_code == 200


# ---------- changing your own password ----------


def test_a_change_needs_the_current_password(admin: TestClient) -> None:
    response = admin.post(
        f"{API}/auth/change-password",
        json={"current_password": "not-the-password", "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 401
    assert "current password" in response.json()["detail"]
    assert sign_in(browser(), "ada@example.com", ADA_PASSWORD).status_code == 200


def test_guessing_the_current_password_is_limited(admin: TestClient) -> None:
    body = {"current_password": "guess-guess-guess", "new_password": NEW_PASSWORD}
    for _ in range(5):
        assert admin.post(f"{API}/auth/change-password", json=body).status_code == 401

    stopped = admin.post(f"{API}/auth/change-password", json=body)
    assert stopped.status_code == 429
    # Even the right password is refused for now: the point is to stop guessing.
    right = admin.post(
        f"{API}/auth/change-password",
        json={"current_password": ADA_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert right.status_code == 429


def test_the_new_password_must_meet_the_rules(admin: TestClient) -> None:
    response = admin.post(
        f"{API}/auth/change-password",
        json={"current_password": ADA_PASSWORD, "new_password": "Welcome2024!!"},
    )

    assert response.status_code == 400
    assert "common" in response.json()["detail"]


def test_a_password_cannot_be_reused(admin: TestClient) -> None:
    def change(current: str, new: str):
        return admin.post(
            f"{API}/auth/change-password", json={"current_password": current, "new_password": new}
        )

    assert change(ADA_PASSWORD, "first-new-passphrase").status_code == 200
    again = change("first-new-passphrase", "first-new-passphrase")
    original = change("first-new-passphrase", ADA_PASSWORD)

    assert again.status_code == 400
    assert original.status_code == 400
    assert "recently" in original.json()["detail"]


def test_only_the_last_few_passwords_are_remembered(admin: TestClient, db_session: Session) -> None:
    user_id = admin.get(f"{API}/auth/me").json()["id"]
    chain = [ADA_PASSWORD] + [f"passphrase-number-{n}-here" for n in range(1, 7)]
    for current, new in zip(chain, chain[1:], strict=False):
        response = admin.post(
            f"{API}/auth/change-password", json={"current_password": current, "new_password": new}
        )
        assert response.status_code == 200, response.text

    # Seven passwords used; the current one and the four before it are barred,
    # the two oldest are free again, and the store holds no more than four.
    assert db_session.query(PasswordHistory).filter_by(user_id=user_id).count() == 4
    current = chain[-1]

    def try_reuse(candidate: str) -> int:
        return admin.post(
            f"{API}/auth/change-password",
            json={"current_password": current, "new_password": candidate},
        ).status_code

    assert try_reuse(chain[-2]) == 400  # the one before the current
    assert try_reuse(chain[-5]) == 400  # four back: still remembered
    assert try_reuse(chain[0]) == 200  # the original: forgotten


def test_a_change_signs_out_every_other_device_but_not_this_one(admin: TestClient) -> None:
    other_device = browser()
    assert sign_in(other_device, "ada@example.com", ADA_PASSWORD).status_code == 200
    assert other_device.get(f"{API}/policies").status_code == 200

    response = admin.post(
        f"{API}/auth/change-password",
        json={"current_password": ADA_PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 200
    assert admin.get(f"{API}/policies").status_code == 200
    assert other_device.get(f"{API}/policies").status_code == 401
    assert sign_in(browser(), "ada@example.com", ADA_PASSWORD).status_code == 401
    assert sign_in(browser(), "ada@example.com", NEW_PASSWORD).status_code == 200


def test_changing_the_password_is_recorded(admin: TestClient, db_session: Session) -> None:
    user_id = admin.get(f"{API}/auth/me").json()["id"]
    admin.post(
        f"{API}/auth/change-password",
        json={"current_password": ADA_PASSWORD, "new_password": NEW_PASSWORD},
    )

    [entry] = audit(db_session, user_id, "password_changed")
    assert entry.actor_id == user_id
    assert NEW_PASSWORD not in str(entry.diff) and ADA_PASSWORD not in str(entry.diff)


def test_changing_a_password_needs_a_session(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        f"{API}/auth/change-password",
        json={"current_password": "x", "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 401


def test_sign_out_everywhere_keeps_only_this_session(admin: TestClient) -> None:
    other_device = browser()
    sign_in(other_device, "ada@example.com", ADA_PASSWORD)

    response = admin.post(f"{API}/auth/sign-out-everywhere")

    assert response.json() == {"other_sessions_ended": 1}
    assert admin.get(f"{API}/policies").status_code == 200
    assert other_device.get(f"{API}/policies").status_code == 401


# ---------- an administrator resetting a password ----------


def test_an_admin_can_reset_a_password_and_the_person_must_replace_it(
    admin: TestClient, db_session: Session
) -> None:
    person, bob = settled_person(admin)

    response = admin.post(f"{API}/users/{person['id']}/reset-password")

    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    assert len(temporary) >= 12
    # Whatever Bob had open is gone, his old password no longer works,
    # and the temporary one gets him only as far as the change screen.
    assert bob.get(f"{API}/policies").status_code == 401
    assert sign_in(browser(), "bob@example.com", NEW_PASSWORD).status_code == 401
    fresh = browser()
    assert sign_in(fresh, "bob@example.com", temporary).status_code == 200
    assert fresh.get(f"{API}/policies").status_code == 403
    assert fresh.get(f"{API}/auth/me").json()["must_change_password"] is True
    assert (
        fresh.post(
            f"{API}/auth/change-password",
            json={"current_password": temporary, "new_password": "bobs-own-passphrase-2"},
        ).status_code
        == 200
    )
    assert fresh.get(f"{API}/policies").status_code == 200

    [entry] = audit(db_session, person["id"], "password_reset")
    assert temporary not in str(entry.diff)


def test_a_reset_password_is_different_each_time(admin: TestClient) -> None:
    person = create_person(admin, "bob@example.com")

    first = admin.post(f"{API}/users/{person['id']}/reset-password").json()
    second = admin.post(f"{API}/users/{person['id']}/reset-password").json()

    assert first["temporary_password"] != second["temporary_password"]


def test_a_reset_cannot_return_to_the_password_it_replaced(admin: TestClient) -> None:
    person, _ = settled_person(admin)
    reset = admin.post(f"{API}/users/{person['id']}/reset-password")
    temporary = reset.json()["temporary_password"]
    bob = browser()
    sign_in(bob, "bob@example.com", temporary)

    response = bob.post(
        f"{API}/auth/change-password",
        json={"current_password": temporary, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 400


def test_an_admin_cannot_reset_their_own_password_this_way(admin: TestClient) -> None:
    me = admin.get(f"{API}/auth/me").json()

    assert admin.post(f"{API}/users/{me['id']}/reset-password").status_code == 409


def test_resetting_an_unknown_account_is_not_found(admin: TestClient) -> None:
    assert admin.post(f"{API}/users/9999/reset-password").status_code == 404


def test_only_someone_who_manages_users_can_reset_a_password(
    admin: TestClient,
) -> None:
    person, bob = settled_person(admin)
    other = create_person(admin, "carol@example.com")

    assert bob.post(f"{API}/users/{other['id']}/reset-password").status_code == 403
    assert browser().post(f"{API}/users/{person['id']}/reset-password").status_code == 401


# ---------- sessions follow what the account may do ----------


def test_changing_a_role_ends_that_persons_sessions(admin: TestClient) -> None:
    person, bob = settled_person(admin)
    assert bob.get(f"{API}/policies").status_code == 200

    admin.patch(f"{API}/users/{person['id']}", json={"role": "viewer"})

    assert bob.get(f"{API}/policies").status_code == 401
    assert sign_in(bob, "bob@example.com", NEW_PASSWORD).status_code == 200


def test_deactivating_an_account_removes_its_sessions(
    admin: TestClient, db_session: Session
) -> None:
    person, bob = settled_person(admin)

    admin.patch(f"{API}/users/{person['id']}", json={"is_active": False})

    assert db_session.query(SessionRow).filter_by(user_id=person["id"]).count() == 0
    assert bob.get(f"{API}/policies").status_code == 401


def test_reactivating_does_not_bring_old_sessions_back(admin: TestClient) -> None:
    person, bob = settled_person(admin)
    admin.patch(f"{API}/users/{person['id']}", json={"is_active": False})

    admin.patch(f"{API}/users/{person['id']}", json={"is_active": True})

    assert bob.get(f"{API}/policies").status_code == 401


def test_expired_sessions_are_cleared_at_sign_in(admin: TestClient, db_session: Session) -> None:
    person = create_person(admin, "bob@example.com")
    db_session.add(
        SessionRow(
            token_hash="e" * 64,
            user_id=person["id"],
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    db_session.commit()

    sign_in(browser(), "ada@example.com", ADA_PASSWORD)

    assert db_session.query(SessionRow).filter_by(token_hash="e" * 64).count() == 0


# ---------- the trail ----------


def test_sign_in_and_sign_out_are_recorded_with_the_address(
    unauthenticated_client: TestClient, make_user: Callable[..., User], db_session: Session
) -> None:
    user = make_user(email="ada@example.com", password_hash=hash_password(ADA_PASSWORD))

    sign_in(unauthenticated_client, "ada@example.com", ADA_PASSWORD)
    unauthenticated_client.post(f"{API}/auth/logout")

    [login] = audit(db_session, user.id, "login")
    assert (login.actor_id, login.diff) == (user.id, {"ip": "testclient"})
    [logout] = audit(db_session, user.id, "logout")
    assert logout.actor_id == user.id


def test_a_failed_sign_in_is_recorded_against_the_account(
    unauthenticated_client: TestClient, make_user: Callable[..., User], db_session: Session
) -> None:
    user = make_user(email="ada@example.com", password_hash=hash_password(ADA_PASSWORD))

    sign_in(unauthenticated_client, "ada@example.com", "wrong-wrong-wrong")

    [failed] = audit(db_session, user.id, "login_failed")
    assert (failed.actor_id, failed.diff) == (None, {"ip": "testclient"})
    assert audit(db_session, user.id, "login") == []


def test_a_lockout_is_recorded_once_when_it_starts(
    unauthenticated_client: TestClient, make_user: Callable[..., User], db_session: Session
) -> None:
    user = make_user(email="ada@example.com", password_hash=hash_password(ADA_PASSWORD))

    for _ in range(8):
        sign_in(unauthenticated_client, "ada@example.com", "wrong-wrong-wrong")

    assert len(audit(db_session, user.id, "login_failed")) == 5
    assert len(audit(db_session, user.id, "account_locked")) == 1
    # Locked means locked: the right password is refused too.
    assert sign_in(unauthenticated_client, "ada@example.com", ADA_PASSWORD).status_code == 429


def test_a_good_sign_in_clears_earlier_mistakes(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user(email="ada@example.com", password_hash=hash_password(ADA_PASSWORD))
    for _ in range(4):
        sign_in(unauthenticated_client, "ada@example.com", "wrong-wrong-wrong")
    assert sign_in(unauthenticated_client, "ada@example.com", ADA_PASSWORD).status_code == 200

    # Four more slips would be eight in a row without the reset; with it, they
    # are a fresh four and the account is not locked.
    for _ in range(4):
        sign_in(unauthenticated_client, "ada@example.com", "wrong-wrong-wrong")

    assert sign_in(unauthenticated_client, "ada@example.com", ADA_PASSWORD).status_code == 200


def test_an_unknown_email_leaves_no_trace_to_probe(
    unauthenticated_client: TestClient, db_session: Session
) -> None:
    sign_in(unauthenticated_client, "nobody@example.com", "wrong-wrong-wrong")

    assert db_session.query(AuditLogEntry).filter_by(action="login_failed").count() == 0


def test_one_address_trying_many_accounts_is_stopped(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    for n in range(20):
        make_user(email=f"person{n}@example.com", password_hash=hash_password(ADA_PASSWORD))
        # Each account is tried once, so none reaches its own limit.
        assert sign_in(unauthenticated_client, f"person{n}@example.com", "wrong").status_code == 401

    response = sign_in(unauthenticated_client, "person0@example.com", ADA_PASSWORD)

    assert response.status_code == 429
    assert "this address" in response.json()["detail"]


def test_a_successful_sign_in_does_not_clear_the_address_count(
    unauthenticated_client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user(email="mine@example.com", password_hash=hash_password(ADA_PASSWORD))
    for n in range(20):
        sign_in(unauthenticated_client, f"nobody{n}@example.com", "wrong")

    # An attacker with an account of their own can't reset their count by using it.
    assert sign_in(unauthenticated_client, "mine@example.com", ADA_PASSWORD).status_code == 429


def test_an_employee_login_can_change_its_password_too(
    admin: TestClient,
) -> None:
    create_person(admin, "elena@example.com", role=UserRole.EMPLOYEE.value)
    elena = browser()
    sign_in(elena, "elena@example.com", "temporary-passphrase-1")

    assert elena.get(f"{API}/staff/ai-use-notice").status_code == 403
    assert (
        elena.post(
            f"{API}/auth/change-password",
            json={"current_password": "temporary-passphrase-1", "new_password": NEW_PASSWORD},
        ).status_code
        == 200
    )
    assert elena.get(f"{API}/staff/ai-use-notice").status_code == 200
