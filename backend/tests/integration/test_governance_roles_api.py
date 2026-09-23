from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.user import UserRole


def role_id(client: TestClient, name: str) -> int:
    roles = client.get("/api/v1/governance-roles").json()
    return next(r["id"] for r in roles if r["name"] == name)


def holder_ids(client: TestClient, role_id_: int) -> list[int]:
    # There is no GET /governance-roles/{id} -- the list endpoint is the
    # only place a role's current holders can be read back from.
    roles = client.get("/api/v1/governance-roles").json()
    role = next(r for r in roles if r["id"] == role_id_)
    return [h["id"] for h in role["holders"]]


def test_list_roles_is_open_to_any_logged_in_user(client: TestClient) -> None:
    response = client.get("/api/v1/governance-roles")

    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert "Chief AI Governance Officer" in names
    assert "Risk Owner" in names


def test_org_chart_shows_the_seeded_hierarchy(client: TestClient) -> None:
    chart = client.get("/api/v1/governance-roles/org-chart").json()

    caigo = next(n for n in chart if n["name"] == "Chief AI Governance Officer")
    risk_owner = next(n for n in chart if n["name"] == "Risk Owner")
    assert caigo["parent_role_id"] is None
    assert risk_owner["parent_role_id"] == caigo["id"]


def test_creating_a_role_requires_manage_users(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    response = client.post(
        "/api/v1/governance-roles",
        json={"name": "Vendor Manager", "responsibilities": "Owns vendor relationships."},
    )

    assert response.status_code == 403


def test_admin_can_create_and_assign_a_role(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))

    created = client.post(
        "/api/v1/governance-roles",
        json={"name": "Vendor Manager", "responsibilities": "Owns vendor relationships."},
    )
    assert created.status_code == 201
    new_role_id = created.json()["id"]

    target = make_user()
    assigned = client.post(
        f"/api/v1/governance-roles/{new_role_id}/assignments", json={"user_id": target.id}
    )

    assert assigned.status_code == 201
    assert [h["id"] for h in assigned.json()["holders"]] == [target.id]


def test_assigning_caigo_to_a_non_admin_is_rejected(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    contributor = make_user(role=UserRole.CONTRIBUTOR)

    response = client.post(
        f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": contributor.id}
    )

    assert response.status_code == 400


def test_a_second_caigo_assignment_is_rejected(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    first_admin = make_user(role=UserRole.ADMIN)
    second_admin = make_user(role=UserRole.ADMIN)
    client.post(f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": first_admin.id})

    response = client.post(
        f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": second_admin.id}
    )

    assert response.status_code == 409


def test_unassigning_requires_manage_users(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    risk_owner = role_id(client, "Risk Owner")
    target = make_user()
    client.post(f"/api/v1/governance-roles/{risk_owner}/assignments", json={"user_id": target.id})

    login_as(make_user(role=UserRole.VIEWER))
    response = client.delete(f"/api/v1/governance-roles/{risk_owner}/assignments/{target.id}")

    assert response.status_code == 403


def test_deleting_caigo_is_rejected(client: TestClient, make_user, login_as) -> None:
    """Every approval in the app is gated on this role being findable by
    name, so it can't be deleted any more than it can be renamed."""
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    # Move the seeded children off it, so the has-children guard isn't the
    # thing doing the refusing.
    for role in client.get("/api/v1/governance-roles").json():
        if role["parent_role_id"] == caigo:
            client.patch(
                f"/api/v1/governance-roles/{role['id']}", json={"parent_role_id": None}
            )

    response = client.delete(f"/api/v1/governance-roles/{caigo}")

    assert response.status_code == 409


def test_renaming_caigo_is_rejected(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")

    response = client.patch(
        f"/api/v1/governance-roles/{caigo}", json={"name": "Head of AI Governance"}
    )

    assert response.status_code == 400


def test_deleting_a_role_with_children_is_blocked(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")

    response = client.delete(f"/api/v1/governance-roles/{caigo}")

    assert response.status_code == 409


def test_user_directory_badges_governance_roles(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    risk_owner = role_id(client, "Risk Owner")
    target = make_user()
    client.post(f"/api/v1/governance-roles/{risk_owner}/assignments", json={"user_id": target.id})

    directory = client.get("/api/v1/users/directory").json()

    entry = next(u for u in directory if u["id"] == target.id)
    assert entry["governance_roles"] == ["Risk Owner"]


def test_user_with_no_governance_role_has_an_empty_badge_list(
    client: TestClient, make_user
) -> None:
    other = make_user()

    directory = client.get("/api/v1/users/directory").json()

    entry = next(u for u in directory if u["id"] == other.id)
    assert entry["governance_roles"] == []


def test_get_caigo_delegation_is_null_with_no_active_delegation(client: TestClient) -> None:
    response = client.get("/api/v1/governance-roles/caigo-delegation")

    assert response.status_code == 200
    assert response.json() is None


def test_setting_a_caigo_delegation_requires_manage_users(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.CONTRIBUTOR))
    delegate = make_user(role=UserRole.ADMIN)

    response = client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={
            "delegate_user_id": delegate.id,
            "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 403


def test_admin_can_set_and_read_back_a_caigo_delegation(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    delegate = make_user(role=UserRole.ADMIN, name="Backup Approver")
    ends_at = datetime.now(UTC) + timedelta(days=3)

    created = client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={"delegate_user_id": delegate.id, "ends_at": ends_at.isoformat()},
    )
    assert created.status_code == 201
    assert created.json()["delegate_user_id"] == delegate.id
    assert created.json()["delegate_name"] == "Backup Approver"

    fetched = client.get("/api/v1/governance-roles/caigo-delegation")
    assert fetched.status_code == 200
    assert fetched.json()["delegate_user_id"] == delegate.id


def test_delegating_to_a_non_admin_is_rejected(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    contributor = make_user(role=UserRole.CONTRIBUTOR)

    response = client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={
            "delegate_user_id": contributor.id,
            "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 400


def test_revoking_a_caigo_delegation_requires_manage_users(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    delegate = make_user(role=UserRole.ADMIN)
    client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={
            "delegate_user_id": delegate.id,
            "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    login_as(make_user(role=UserRole.CONTRIBUTOR))
    response = client.delete("/api/v1/governance-roles/caigo-delegation")

    assert response.status_code == 403


def test_admin_can_revoke_a_caigo_delegation(client: TestClient, make_user, login_as) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    delegate = make_user(role=UserRole.ADMIN)
    client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={
            "delegate_user_id": delegate.id,
            "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    response = client.delete("/api/v1/governance-roles/caigo-delegation")

    assert response.status_code == 204
    assert client.get("/api/v1/governance-roles/caigo-delegation").json() is None


def test_revoking_with_no_active_delegation_is_rejected(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))

    response = client.delete("/api/v1/governance-roles/caigo-delegation")

    assert response.status_code == 400


def test_removing_the_sole_caigo_holder_with_no_delegate_is_rejected(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    holder = make_user(role=UserRole.ADMIN)
    client.post(f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": holder.id})

    response = client.delete(f"/api/v1/governance-roles/{caigo}/assignments/{holder.id}")

    assert response.status_code == 409
    assert "only person" in response.json()["detail"]
    # Refused, not just warned about -- the holder is still assigned.
    assert holder_ids(client, caigo) == [holder.id]


def test_removing_a_caigo_holder_is_allowed_once_a_backup_approver_is_set(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    holder = make_user(role=UserRole.ADMIN)
    delegate = make_user(role=UserRole.ADMIN)
    client.post(f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": holder.id})
    client.post(
        "/api/v1/governance-roles/caigo-delegation",
        json={
            "delegate_user_id": delegate.id,
            "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    response = client.delete(f"/api/v1/governance-roles/{caigo}/assignments/{holder.id}")

    assert response.status_code == 200
    assert holder_ids(client, caigo) == []


def test_removing_one_of_two_caigo_holders_is_allowed(
    client: TestClient, make_user, login_as
) -> None:
    """CAIGO is capped at one holder by the seeded default, but the cap
    itself is just a governance_roles.max_holders value -- raising it (as an
    admin legitimately could) has to widen this guard too, not just the
    seeded case."""
    login_as(make_user(role=UserRole.ADMIN))
    caigo = role_id(client, "Chief AI Governance Officer")
    client.patch(f"/api/v1/governance-roles/{caigo}", json={"max_holders": 2})
    first = make_user(role=UserRole.ADMIN)
    second = make_user(role=UserRole.ADMIN)
    client.post(f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": first.id})
    client.post(f"/api/v1/governance-roles/{caigo}/assignments", json={"user_id": second.id})

    response = client.delete(f"/api/v1/governance-roles/{caigo}/assignments/{first.id}")

    assert response.status_code == 200
    assert holder_ids(client, caigo) == [second.id]


def test_removing_a_non_caigo_role_holder_is_unaffected_by_the_guard(
    client: TestClient, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.ADMIN))
    risk_owner = role_id(client, "Risk Owner")
    holder = make_user()
    client.post(f"/api/v1/governance-roles/{risk_owner}/assignments", json={"user_id": holder.id})

    response = client.delete(f"/api/v1/governance-roles/{risk_owner}/assignments/{holder.id}")

    assert response.status_code == 200
    assert holder_ids(client, risk_owner) == []
