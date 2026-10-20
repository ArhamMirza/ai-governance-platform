"""Importing staff accounts from a CSV: a preview that changes nothing, an
import that can be run twice, the starting passwords, and what a file is
never allowed to do. Through the real cookie flow, like the account tests."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry
from app.models.user import User, UserRole
from app.services import user_service

API = "/api/v1"
ADA_PASSWORD = "tangerine-lantern-47"
HEADER = "name,email,role\n"


def browser() -> TestClient:
    from app.main import app

    return TestClient(app)


def sign_in(client: TestClient, email: str, password: str):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


@pytest.fixture()
def admin(unauthenticated_client: TestClient) -> TestClient:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada Admin", "email": "ada@example.com", "password": ADA_PASSWORD},
    )
    assert response.status_code == 201
    return unauthenticated_client


def upload(client: TestClient, path: str, text: str | bytes, name: str = "staff.csv"):
    content = text.encode() if isinstance(text, str) else text
    return client.post(f"{API}{path}", files={"file": (name, content, "text/csv")})


def preview(client: TestClient, text: str | bytes):
    return upload(client, "/users/import/preview", text)


def run(client: TestClient, text: str | bytes):
    return upload(client, "/users/import", text)


def users(client: TestClient) -> dict[str, dict]:
    return {u["email"]: u for u in client.get(f"{API}/users").json()}


def create_person(
    admin: TestClient, email: str, role: str = "contributor", name: str = "Bob"
) -> dict:
    response = admin.post(
        f"{API}/users",
        json={"name": name, "email": email, "password": "temporary-passphrase-1", "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------- the preview ----------


def test_a_preview_says_what_would_happen_and_changes_nothing(admin: TestClient) -> None:
    before = users(admin)

    response = preview(
        admin,
        HEADER + "Elena Ortiz,elena@example.com,employee\nSam Rivera,sam@example.com,viewer\n",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["create"], body["update"], body["unchanged"], body["skip"]) == (2, 0, 0, 0)
    assert [r["action"] for r in body["rows"]] == ["create", "create"]
    assert users(admin) == before


def test_each_line_is_judged_on_its_own_with_a_reason(
    admin: TestClient, db_session: Session
) -> None:
    create_person(admin, "same@example.com", role="viewer", name="Same Person")
    create_person(admin, "rename@example.com", role="viewer", name="Old Name")
    create_person(admin, "promote@example.com", role="viewer", name="Pat Promote")
    create_person(admin, "boss@example.com", role="admin", name="Boss")
    gone = create_person(admin, "gone@example.com", role="viewer", name="Gone Person")
    admin.patch(f"{API}/users/{gone['id']}", json={"is_active": False})

    text = (
        HEADER
        + "Same Person,same@example.com,viewer\n"  # unchanged
        + "New Name,rename@example.com,\n"  # name only; blank role leaves the role
        + "Pat Promote,promote@example.com,contributor\n"  # role change
        + "Boss,boss@example.com,viewer\n"  # existing admin: refused
        + "Gone Person,gone@example.com,viewer\n"  # deactivated: refused
        + "Ada Admin,ada@example.com,viewer\n"  # yourself: refused
        + "Nobody,not-an-email,viewer\n"
        + ",blank@example.com,viewer\n"
        + "Eve,eve@example.com,admin\n"
        + "Wally,wally@example.com,wizard\n"
        + "Dup One,dup@example.com,viewer\n"
        + "Dup Two,DUP@example.com,viewer\n"
    )

    rows = {r["email"]: r for r in preview(admin, text).json()["rows"]}

    assert rows["same@example.com"]["action"] == "unchanged"
    assert rows["rename@example.com"]["action"] == "update"
    assert "name 'Old Name' to 'New Name'" in rows["rename@example.com"]["note"]
    assert "role" not in rows["rename@example.com"]["note"]
    assert rows["promote@example.com"]["action"] == "update"
    assert "viewer to contributor" in rows["promote@example.com"]["note"]
    assert rows["boss@example.com"]["action"] == "skip"
    assert rows["gone@example.com"]["action"] == "skip"
    assert "Deactivated" in rows["gone@example.com"]["note"]
    assert "your own" in rows["ada@example.com"]["note"]
    assert rows["not-an-email"]["action"] == "skip"
    assert rows["blank@example.com"]["note"] == "No name."
    assert "one at a time" in rows["eve@example.com"]["note"]
    assert "Unknown role 'wizard'" in rows["wally@example.com"]["note"]
    dups = [r for r in preview(admin, text).json()["rows"] if r["email"] == "dup@example.com"]
    assert [r["action"] for r in dups] == ["create", "skip"]
    assert dups[1]["note"] == "Appears twice in the file (first on line 12)."


def test_someone_with_no_role_in_the_file_becomes_an_employee(admin: TestClient) -> None:
    body = preview(admin, "name,email\nElena,elena@example.com\n").json()

    assert body["rows"][0]["role"] == "employee"


def test_people_who_are_not_in_the_file_are_listed_but_never_touched(admin: TestClient) -> None:
    create_person(admin, "stays@example.com", name="Stays")
    leaver = create_person(admin, "leaver@example.com", name="Leaver")
    inactive = create_person(admin, "inactive@example.com", name="Inactive")
    admin.patch(f"{API}/users/{inactive['id']}", json={"is_active": False})

    body = run(admin, HEADER + "Stays,stays@example.com,contributor\n").json()

    missing = [m["email"] for m in body["missing_from_file"]]
    assert missing == ["leaver@example.com"]  # not you, not someone already deactivated
    assert users(admin)["leaver@example.com"]["is_active"] is True
    assert leaver["is_active"] is True
    assert preview(admin, HEADER + "A,a@example.com,\n").json()["missing_from_file"]


# ---------- the import ----------


def test_the_import_creates_accounts_with_passwords_that_work_once(admin: TestClient) -> None:
    response = run(
        admin, HEADER + "Elena Ortiz,elena@example.com,employee\nSam,sam@example.com,viewer\n"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {c["email"]: c["role"] for c in body["created"]} == {
        "elena@example.com": "employee",
        "sam@example.com": "viewer",
    }
    assert users(admin)["elena@example.com"]["must_change_password"] is True

    elena = next(c for c in body["created"] if c["email"] == "elena@example.com")
    person = browser()
    signed_in = sign_in(person, "elena@example.com", elena["temporary_password"])
    assert signed_in.status_code == 200
    assert signed_in.json()["must_change_password"] is True
    # Until she chooses her own, nothing but the change-password screen opens.
    assert person.get(f"{API}/staff/ai-use-notice").status_code in (401, 403)
    changed = person.post(
        f"{API}/auth/change-password",
        json={
            "current_password": elena["temporary_password"],
            "new_password": "a-much-better-passphrase",
        },
    )
    assert changed.status_code == 200, changed.text
    assert sign_in(browser(), "elena@example.com", elena["temporary_password"]).status_code == 401


def test_every_password_is_different_and_safe_to_paste_into_a_spreadsheet(
    admin: TestClient,
) -> None:
    rows = "".join(f"Person {i},p{i}@example.com,employee\n" for i in range(12))

    passwords = [c["temporary_password"] for c in run(admin, HEADER + rows).json()["created"]]

    assert len(set(passwords)) == 12
    assert all(len(p) >= 12 and p[0].isalnum() for p in passwords)


def test_the_passwords_are_not_kept_anywhere_readable(
    admin: TestClient, db_session: Session
) -> None:
    body = run(admin, HEADER + "Elena,elena@example.com,employee\n").json()
    password = body["created"][0]["temporary_password"]

    stored = db_session.query(User).filter_by(email="elena@example.com").one()
    assert password not in stored.password_hash
    trail = " ".join(str(e.diff) for e in db_session.query(AuditLogEntry).all())
    assert password not in trail
    summary = db_session.query(AuditLogEntry).filter_by(action="imported_users").one()
    assert summary.diff == {"created": 1, "updated": 0, "unchanged": 0, "skipped": 0}


def test_running_the_same_file_again_changes_nothing(admin: TestClient) -> None:
    text = HEADER + "Elena,elena@example.com,employee\nSam,sam@example.com,viewer\n"
    first = run(admin, text).json()
    second = run(admin, text).json()

    assert len(first["created"]) == 2
    assert second["created"] == []
    assert second["unchanged"] == 2
    assert len(users(admin)) == 3


def test_a_corrected_file_fixes_names_and_roles_and_signs_the_person_out(admin: TestClient) -> None:
    run(admin, HEADER + "Elena Ortis,elena@example.com,employee\n")
    created = users(admin)["elena@example.com"]
    assert created["name"] == "Elena Ortis"
    # A role change must not leave the old session running on the old terms.
    pat = create_person(admin, "pat@example.com", role="viewer", name="Pat")
    pat_browser = browser()
    assert sign_in(pat_browser, "pat@example.com", "temporary-passphrase-1").status_code == 200

    result = run(
        admin,
        HEADER + "Elena Ortiz,elena@example.com,\nPat,pat@example.com,contributor\n",
    ).json()

    assert result["updated"] == 2
    after = users(admin)
    assert after["elena@example.com"]["name"] == "Elena Ortiz"
    assert after["elena@example.com"]["role"] == "employee"
    assert after["pat@example.com"]["role"] == "contributor"
    assert pat_browser.get(f"{API}/auth/me").status_code == 401
    assert pat["id"] == after["pat@example.com"]["id"]


def test_a_file_can_never_make_an_administrator_or_change_one(admin: TestClient) -> None:
    create_person(admin, "boss@example.com", role="admin", name="Boss")

    result = run(
        admin,
        HEADER
        + "Eve,eve@example.com,admin\nBoss,boss@example.com,viewer\n"
        + "Ada Admin,ada@example.com,viewer\n",
    ).json()

    assert result["created"] == [] and result["updated"] == 0
    assert len(result["skipped"]) == 3
    after = users(admin)
    assert "eve@example.com" not in after
    assert after["boss@example.com"]["role"] == "admin"
    assert after["ada@example.com"]["role"] == "admin"


def test_the_import_does_not_trust_a_preview(admin: TestClient) -> None:
    text = HEADER + "Elena,elena@example.com,employee\n"
    assert preview(admin, text).json()["create"] == 1
    create_person(admin, "elena@example.com", role="viewer", name="Elena")

    result = run(admin, text).json()

    assert result["created"] == []
    assert result["unchanged"] == 0  # her role differs from the file's, so it is an update
    assert result["updated"] == 1


# ---------- reading the file ----------


def test_a_spreadsheet_export_is_understood(admin: TestClient) -> None:
    # Excel: a byte-order mark, semicolons in some countries, its own column names.
    text = "﻿Full Name;E-mail;Role\nElena Ortiz;elena@example.com;Employee\n"

    body = preview(admin, text.encode("utf-8")).json()

    assert (body["rows"][0]["email"], body["rows"][0]["role"]) == ("elena@example.com", "employee")


def test_blank_lines_and_quoted_commas_are_handled(admin: TestClient) -> None:
    text = HEADER + '"Ortiz, Elena",elena@example.com,employee\n\n,,\nSam,sam@example.com,viewer\n'

    body = preview(admin, text).json()

    assert [r["name"] for r in body["rows"]] == ["Ortiz, Elena", "Sam"]
    assert body["rows"][1]["line"] == 5


@pytest.mark.parametrize(
    ("content", "fragment"),
    [
        ("", "empty"),
        ("   \n", "empty"),
        ("email,role\nelena@example.com,employee\n", "'name' and 'email'"),
        ("name,email\n", "no people"),
        (b"name,email\n\xff\xfe\n", "UTF-8"),
    ],
)
def test_a_file_that_cannot_be_read_is_refused_with_a_reason(
    admin: TestClient, content: str | bytes, fragment: str
) -> None:
    for send in (preview, run):
        response = send(admin, content)
        assert response.status_code == 400, response.text
        assert fragment in response.json()["detail"]


def test_a_file_with_too_many_people_is_refused(admin: TestClient) -> None:
    rows = "".join(f"P{i},p{i}@example.com,employee\n" for i in range(201))

    response = preview(admin, "name,email,role\n" + rows)

    assert response.status_code == 400
    assert "200" in response.json()["detail"]
    assert preview(admin, "name,email,role\n" + rows[: rows.index("\n", 5000)]).status_code == 200


def test_a_file_that_is_too_large_is_refused(admin: TestClient) -> None:
    response = preview(admin, HEADER + "A," + "x" * 1_100_000 + "@example.com,viewer\n")

    assert response.status_code == 400


# ---------- who may do it ----------


@pytest.mark.parametrize("role", ["contributor", "viewer", "employee"])
def test_only_an_administrator_can_import(admin: TestClient, role: str) -> None:
    create_person(admin, "other@example.com", role=role)
    other = browser()
    assert sign_in(other, "other@example.com", "temporary-passphrase-1").status_code == 200
    other.post(
        f"{API}/auth/change-password",
        json={
            "current_password": "temporary-passphrase-1",
            "new_password": "a-much-better-passphrase",
        },
    )

    for send in (preview, run):
        assert send(other, HEADER + "A,a@example.com,\n").status_code == 403


def test_a_stranger_cannot_import(unauthenticated_client: TestClient) -> None:
    for send in (preview, run):
        assert send(unauthenticated_client, HEADER + "A,a@example.com,\n").status_code == 401


# ---------- starting passwords expire ----------


def test_a_starting_password_stops_working_after_a_week(
    admin: TestClient, db_session: Session
) -> None:
    body = run(admin, HEADER + "Elena,elena@example.com,employee\n").json()
    password = body["created"][0]["temporary_password"]
    assert body["password_expires_on"] == (datetime.now(UTC) + timedelta(days=7)).date().isoformat()

    user = db_session.query(User).filter_by(email="elena@example.com").one()
    user.temporary_password_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    response = sign_in(browser(), "elena@example.com", password)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]
    # A wrong guess learns nothing about that.
    wrong = sign_in(browser(), "elena@example.com", "not-her-password-1")
    assert "expired" not in wrong.json()["detail"]

    # An administrator issuing a fresh one starts the clock again.
    reset = admin.post(f"{API}/users/{user.id}/reset-password").json()["temporary_password"]
    assert sign_in(browser(), "elena@example.com", reset).status_code == 200


def test_choosing_your_own_password_ends_the_expiry(admin: TestClient, db_session: Session) -> None:
    create_person(admin, "bob@example.com")
    bob = browser()
    assert sign_in(bob, "bob@example.com", "temporary-passphrase-1").status_code == 200
    bob.post(
        f"{API}/auth/change-password",
        json={
            "current_password": "temporary-passphrase-1",
            "new_password": "a-much-better-passphrase",
        },
    )

    user = db_session.query(User).filter_by(email="bob@example.com").one()
    assert user.temporary_password_expires_at is None
    assert sign_in(browser(), "bob@example.com", "a-much-better-passphrase").status_code == 200


def test_accounts_that_predate_the_expiry_are_not_locked_out(
    admin: TestClient, db_session: Session
) -> None:
    create_person(admin, "old@example.com")
    user = db_session.query(User).filter_by(email="old@example.com").one()
    user.temporary_password_expires_at = None
    user.created_at = datetime.now(UTC) - timedelta(days=400)
    db_session.commit()

    assert sign_in(browser(), "old@example.com", "temporary-passphrase-1").status_code == 200


def test_temporary_passwords_never_start_with_a_symbol() -> None:
    for _ in range(300):
        assert user_service.temporary_password("a@example.com", "A")[0].isalnum()
    assert UserRole.EMPLOYEE == "employee"
