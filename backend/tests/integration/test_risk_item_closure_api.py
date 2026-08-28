from fastapi.testclient import TestClient

from tests.helpers import complete_impact_assessment


def create_risk_assessment(client: TestClient) -> dict:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    complete_impact_assessment(client, row["id"])
    return client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}).json()


def add_row(client: TestClient, risk_assessment_id: int, **data) -> dict:
    response = client.post(
        f"/api/v1/risk-assessments/{risk_assessment_id}/rows", json={"data": data}
    )
    assert response.status_code == 201
    return response.json()


def upload_evidence(client: TestClient, row_id: int) -> dict:
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "RiskItem", "entity_id": str(row_id)},
        files={"file": ("mitigation-proof.pdf", b"bytes", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_closing_without_evidence_is_rejected(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias", likelihood=3, impact=3)

    response = client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    assert response.status_code == 400
    assert "evidence" in response.json()["detail"].lower()


def test_closing_with_evidence_succeeds(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias", likelihood=3, impact=3)
    upload_evidence(client, row["id"])

    response = client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "closed"
    assert body["data"]["category"] == "Bias"
    assert "closed_at" in body["data"]
    assert "closed_by" in body["data"]


def test_closing_an_already_closed_item_is_rejected(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias")
    upload_evidence(client, row["id"])
    client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    response = client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    assert response.status_code == 409


def test_closing_a_row_from_a_different_assessment_is_not_found(client: TestClient) -> None:
    ra1 = create_risk_assessment(client)
    ra2 = create_risk_assessment(client)
    row = add_row(client, ra1["id"], category="Bias")
    upload_evidence(client, row["id"])

    response = client.post(f"/api/v1/risk-assessments/{ra2['id']}/rows/{row['id']}/close")

    assert response.status_code == 404


def test_closing_is_audited(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias")
    upload_evidence(client, row["id"])

    client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    history = client.get(
        "/api/v1/audit-log", params={"entity_type": "RiskAssessment", "entity_id": ra["id"]}
    ).json()
    actions = [entry["action"] for entry in history]
    assert "risk_item_closed" in actions


def test_closing_requires_edit_permission(
    client: TestClient, make_user, login_as
) -> None:
    from app.models.user import UserRole

    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias")
    upload_evidence(client, row["id"])

    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}/close")

    assert response.status_code == 403


def test_deleting_a_risk_item_deletes_its_evidence(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias")
    evidence = upload_evidence(client, row["id"])

    delete_response = client.delete(f"/api/v1/risk-assessments/{ra['id']}/rows/{row['id']}")
    assert delete_response.status_code == 204

    download_response = client.get(f"/api/v1/evidence/{evidence['id']}/download")
    assert download_response.status_code == 404


def test_deleting_a_risk_assessment_deletes_all_its_items_evidence(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row1 = add_row(client, ra["id"], category="Bias")
    row2 = add_row(client, ra["id"], category="Privacy")
    evidence1 = upload_evidence(client, row1["id"])
    evidence2 = upload_evidence(client, row2["id"])

    delete_response = client.delete(f"/api/v1/risk-assessments/{ra['id']}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/v1/evidence/{evidence1['id']}/download").status_code == 404
    assert client.get(f"/api/v1/evidence/{evidence2['id']}/download").status_code == 404


def test_risk_item_evidence_is_listable(client: TestClient) -> None:
    ra = create_risk_assessment(client)
    row = add_row(client, ra["id"], category="Bias")
    upload_evidence(client, row["id"])

    response = client.get(
        "/api/v1/evidence", params={"entity_type": "RiskItem", "entity_id": row["id"]}
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
