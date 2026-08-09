from fastapi.testclient import TestClient


def create_folder(client: TestClient, **overrides) -> dict:
    payload = {"entity_type": "Policy", "entity_id": 1, "name": "Signed Versions"}
    payload.update(overrides)
    response = client.post("/api/v1/folders", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_and_list_root_folders(client: TestClient) -> None:
    create_folder(client, name="Folder A")
    create_folder(client, name="Folder B")

    response = client.get("/api/v1/folders", params={"entity_type": "Policy", "entity_id": 1})

    assert response.status_code == 200
    names = {f["name"] for f in response.json()}
    assert names == {"Folder A", "Folder B"}


def test_create_subfolder(client: TestClient) -> None:
    parent = create_folder(client, name="Parent")

    response = client.post(
        "/api/v1/folders",
        json={
            "entity_type": "Policy",
            "entity_id": 1,
            "name": "Child",
            "parent_folder_id": parent["id"],
        },
    )

    assert response.status_code == 201
    assert response.json()["parent_folder_id"] == parent["id"]


def test_subfolder_rejects_mismatched_parent_entity(client: TestClient) -> None:
    parent = create_folder(client, entity_type="Policy", entity_id=1)

    response = client.post(
        "/api/v1/folders",
        json={
            "entity_type": "Procedure",
            "entity_id": 2,
            "name": "Child",
            "parent_folder_id": parent["id"],
        },
    )

    assert response.status_code == 400


def test_rename_folder(client: TestClient) -> None:
    folder = create_folder(client)

    response = client.put(f"/api/v1/folders/{folder['id']}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_get_missing_folder_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/folders/999")
    assert response.status_code == 404


def test_delete_empty_folder(client: TestClient) -> None:
    folder = create_folder(client)

    response = client.delete(f"/api/v1/folders/{folder['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/folders/{folder['id']}").status_code == 404


def test_cannot_delete_folder_with_subfolder(client: TestClient) -> None:
    parent = create_folder(client, name="Parent")
    client.post(
        "/api/v1/folders",
        json={
            "entity_type": "Policy",
            "entity_id": 1,
            "name": "Child",
            "parent_folder_id": parent["id"],
        },
    )

    response = client.delete(f"/api/v1/folders/{parent['id']}")

    assert response.status_code == 409
