"""Every place an email address is typed or sent applies the same rule."""

import pytest
from fastapi.testclient import TestClient

from app.core import email_address

API = "/api/v1"
GOOD_PASSWORD = "tangerine-lantern-47"
BAD = ["bob@x", "bob@@example.com", "bob example.com", "bob@example..com", "@example.com"]


@pytest.fixture()
def admin(unauthenticated_client: TestClient) -> TestClient:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada Admin", "email": "ada@example.com", "password": GOOD_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return unauthenticated_client


@pytest.mark.parametrize("address", BAD)
def test_the_first_account_needs_a_real_looking_address(
    unauthenticated_client: TestClient, address: str
) -> None:
    response = unauthenticated_client.post(
        f"{API}/auth/register",
        json={"name": "Ada", "email": address, "password": GOOD_PASSWORD},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == email_address.MESSAGE


@pytest.mark.parametrize("address", BAD)
def test_creating_an_account_needs_a_real_looking_address(admin: TestClient, address: str) -> None:
    response = admin.post(
        f"{API}/users",
        json={
            "name": "Bob",
            "email": address,
            "password": "temporary-passphrase-1",
            "role": "viewer",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == email_address.MESSAGE
    assert [u["email"] for u in admin.get(f"{API}/users").json()] == ["ada@example.com"]


def test_an_address_is_tidied_before_it_is_stored(admin: TestClient) -> None:
    response = admin.post(
        f"{API}/users",
        json={
            "name": "Bob",
            "email": "  Bob@Example.COM ",
            "password": "temporary-passphrase-1",
            "role": "viewer",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "bob@example.com"


def test_the_csv_import_agrees(admin: TestClient) -> None:
    text = (
        "name,email\n" + "\n".join(f"P{i},{a}" for i, a in enumerate(BAD)) + "\nOk,ok@example.com\n"
    )

    body = admin.post(
        f"{API}/users/import/preview", files={"file": ("p.csv", text.encode(), "text/csv")}
    ).json()

    assert [r["action"] for r in body["rows"]] == ["skip"] * len(BAD) + ["create"]


def test_the_extension_agrees(admin: TestClient) -> None:
    key = admin.post(f"{API}/ai-use/enrollment-key").json()["key"]
    headers = {"Authorization": f"Bearer {key}"}

    for address in BAD:
        checkin = admin.post(f"{API}/agent/checkin", headers=headers, json={"user_email": address})
        assert checkin.status_code == 400, address
    assert (
        admin.post(
            f"{API}/agent/checkin", headers=headers, json={"user_email": "ada@example.com"}
        ).status_code
        == 204
    )
