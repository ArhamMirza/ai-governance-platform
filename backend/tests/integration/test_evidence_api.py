from fastapi.testclient import TestClient


def upload_evidence(client: TestClient, filename: str = "report.pdf", **form_overrides) -> dict:
    form = {"entity_type": "Policy", "entity_id": "1"}
    form.update(form_overrides)
    response = client.post(
        "/api/v1/evidence",
        data=form,
        files={"file": (filename, b"file-bytes", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_upload_and_list_evidence(client: TestClient) -> None:
    uploaded = upload_evidence(client)

    response = client.get(
        "/api/v1/evidence", params={"entity_type": "Policy", "entity_id": 1}
    )

    assert response.status_code == 200
    filenames = [e["filename"] for e in response.json()]
    assert filenames == ["report.pdf"]
    assert uploaded["size_bytes"] == len(b"file-bytes")


def test_upload_rejects_disallowed_extension(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": "1"},
        files={"file": ("malware.exe", b"x", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_download_evidence(client: TestClient) -> None:
    uploaded = upload_evidence(client)

    response = client.get(f"/api/v1/evidence/{uploaded['id']}/download")

    assert response.status_code == 200
    assert response.content == b"file-bytes"


def test_delete_evidence(client: TestClient) -> None:
    uploaded = upload_evidence(client)

    response = client.delete(f"/api/v1/evidence/{uploaded['id']}")

    assert response.status_code == 204
    listing = client.get(
        "/api/v1/evidence", params={"entity_type": "Policy", "entity_id": 1}
    ).json()
    assert listing == []


def test_upload_into_folder(client: TestClient) -> None:
    folder = client.post(
        "/api/v1/folders",
        json={"entity_type": "Policy", "entity_id": 1, "name": "Signed"},
    ).json()

    uploaded = upload_evidence(client, folder_id=str(folder["id"]))

    assert uploaded["folder_id"] == folder["id"]
    root_listing = client.get(
        "/api/v1/evidence", params={"entity_type": "Policy", "entity_id": 1}
    ).json()
    assert root_listing == []
    folder_listing = client.get(
        "/api/v1/evidence",
        params={"entity_type": "Policy", "entity_id": 1, "folder_id": folder["id"]},
    ).json()
    assert len(folder_listing) == 1


def test_upload_rejects_folder_from_different_entity(client: TestClient) -> None:
    folder = client.post(
        "/api/v1/folders",
        json={"entity_type": "Procedure", "entity_id": 2, "name": "Other"},
    ).json()

    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": "1", "folder_id": str(folder["id"])},
        files={"file": ("report.pdf", b"x", "application/pdf")},
    )

    assert response.status_code == 400


def test_folder_with_evidence_cannot_be_deleted(client: TestClient) -> None:
    folder = client.post(
        "/api/v1/folders",
        json={"entity_type": "Policy", "entity_id": 1, "name": "Signed"},
    ).json()
    upload_evidence(client, folder_id=str(folder["id"]))

    response = client.delete(f"/api/v1/folders/{folder['id']}")

    assert response.status_code == 409
