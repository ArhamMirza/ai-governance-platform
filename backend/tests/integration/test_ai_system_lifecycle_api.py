"""The gated walk from Inception to Operation & Monitoring.

Each test satisfies exactly the gate it is about, so a failure points at one
requirement rather than the whole chain.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.services import governance_role_service
from tests.helpers import add_approved_dataset, complete_impact_assessment

LIFECYCLE = "/api/v1/ai-systems/{row_id}/lifecycle"

FULL_INVENTORY = {
    "name": "Resume Screener",
    "description": "Ranks applications.",
    "purpose": "Shortlist applicants.",
    "risk_tier": "high",
    "resource_documentation": "Documented.",
    "data_resources": "Applicant CVs.",
    "tooling_frameworks": "PyTorch.",
    "compute_infrastructure": "2x A100.",
    "hosting_environment": "AWS eu-west-1.",
    "development_team": "ML platform team.",
    "oversight_roles": "Head of Talent.",
}


def make_system(client: TestClient, **overrides) -> int:
    data = {**FULL_INVENTORY, **overrides}
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": data})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def lifecycle(client: TestClient, row_id: int) -> dict:
    response = client.get(LIFECYCLE.format(row_id=row_id))
    assert response.status_code == 200, response.text
    return response.json()


def advance(client: TestClient, row_id: int):
    return client.post(LIFECYCLE.format(row_id=row_id) + "/advance")


def requirement(body: dict, key: str) -> dict:
    return next(r for r in body["requirements"] if r["key"] == key)


def upload(client: TestClient, row_id: int, document_type: str):
    return client.post(
        "/api/v1/evidence",
        data={
            "entity_type": "AISystem",
            "entity_id": str(row_id),
            "document_type": document_type,
        },
        files={"file": (f"{document_type}.pdf", b"content", "application/pdf")},
    )


def add_risk_item(client: TestClient, risk_assessment_id: int, **data) -> None:
    payload = {"category": "Bias", "likelihood": 1, "impact": 1, "status": "open"}
    payload.update(data)
    response = client.post(
        f"/api/v1/risk-assessments/{risk_assessment_id}/rows", json={"data": payload}
    )
    assert response.status_code == 201, response.text


def pass_inception(client: TestClient, row_id: int) -> int:
    """Completes the inception gate; returns the risk assessment id."""
    complete_impact_assessment(client, row_id)
    risk_assessment = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": row_id}
    ).json()
    add_risk_item(client, risk_assessment["id"])
    return risk_assessment["id"]


# --- Inception -------------------------------------------------------------


def test_a_new_system_starts_at_inception(client: TestClient) -> None:
    body = lifecycle(client, make_system(client))

    assert body["current_stage"] == "inception"
    assert body["next_stage_label"] == "Design"
    assert body["can_advance"] is False


def test_inception_gate_lists_what_is_missing(client: TestClient) -> None:
    body = lifecycle(client, make_system(client))

    assert requirement(body, "ai_system_owner")["satisfied"] is False
    assert requirement(body, "impact_assessment_completed")["satisfied"] is False
    assert requirement(body, "risk_assessment_performed")["satisfied"] is False


def test_the_inception_gate_asks_for_an_owner_up_front(
    client: TestClient, make_user
) -> None:
    """Submitting an assessment already requires an owner, so the gate says so
    rather than leaving people to discover it from an error."""
    row_id = make_system(client)
    owner = make_user()

    client.put(
        f"/api/v1/ai-systems/{row_id}/lifecycle/owner", json={"owner_id": owner.id}
    )

    assert requirement(lifecycle(client, row_id), "ai_system_owner")["satisfied"] is True


def test_cannot_advance_while_the_gate_is_unmet(client: TestClient) -> None:
    row_id = make_system(client)

    response = advance(client, row_id)

    assert response.status_code == 400
    assert "impact assessment" in response.text.lower()
    assert lifecycle(client, row_id)["current_stage"] == "inception"


def test_a_risk_assessment_with_no_items_does_not_satisfy_the_gate(
    client: TestClient,
) -> None:
    row_id = make_system(client)
    complete_impact_assessment(client, row_id)
    client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row_id})

    body = lifecycle(client, row_id)

    assert requirement(body, "risk_assessment_performed")["satisfied"] is False


def test_advances_to_design_once_both_assessments_are_done(client: TestClient) -> None:
    row_id = make_system(client)
    pass_inception(client, row_id)

    assert lifecycle(client, row_id)["can_advance"] is True
    response = advance(client, row_id)

    assert response.status_code == 200
    assert response.json()["current_stage"] == "design"


# --- Design ----------------------------------------------------------------


def test_design_gate_requires_a_design_document(client: TestClient) -> None:
    row_id = make_system(client)
    pass_inception(client, row_id)
    advance(client, row_id)

    assert advance(client, row_id).status_code == 400

    assert upload(client, row_id, "design_document").status_code == 201
    assert advance(client, row_id).json()["current_stage"] == "development"


# --- Development -----------------------------------------------------------


def reach_development(client: TestClient, row_id: int) -> None:
    pass_inception(client, row_id)
    advance(client, row_id)
    upload(client, row_id, "design_document")
    advance(client, row_id)


def test_development_gate_names_the_empty_inventory_fields(client: TestClient) -> None:
    row_id = make_system(client, purpose="", oversight_roles="")
    reach_development(client, row_id)

    detail = requirement(lifecycle(client, row_id), "inventory_complete")["detail"]

    assert "Purpose" in detail and "Oversight Roles" in detail


def test_development_gate_requires_a_linked_dataset(client: TestClient) -> None:
    row_id = make_system(client)
    reach_development(client, row_id)

    body = lifecycle(client, row_id)
    assert requirement(body, "inventory_complete")["satisfied"] is True
    assert requirement(body, "data_inventory_entry")["satisfied"] is False

    # An unreviewed dataset doesn't satisfy the gate on its own.
    client.post(
        "/api/v1/data-inventory/rows",
        json={"data": {"dataset_name": "CVs", "ai_system_row_id": str(row_id)}},
    )
    assert requirement(lifecycle(client, row_id), "data_inventory_entry")["satisfied"] is False

    add_approved_dataset(client, row_id, dataset_name="Approved CVs")

    assert advance(client, row_id).json()["current_stage"] == "verification_and_validation"


# --- Verification & Validation ---------------------------------------------


def reach_validation(client: TestClient, row_id: int) -> int:
    risk_assessment_id = pass_inception(client, row_id)
    advance(client, row_id)
    upload(client, row_id, "design_document")
    advance(client, row_id)
    add_approved_dataset(client, row_id)
    advance(client, row_id)
    return risk_assessment_id


def test_validation_gate_blocks_on_an_untreated_high_risk(client: TestClient) -> None:
    row_id = make_system(client)
    risk_assessment_id = reach_validation(client, row_id)
    add_risk_item(client, risk_assessment_id, category="Bias", likelihood=5, impact=5)

    body = lifecycle(client, row_id)

    assert requirement(body, "no_untreated_high_risks")["satisfied"] is False
    assert "Bias" in requirement(body, "no_untreated_high_risks")["detail"]


def test_validation_gate_requires_report_approval_and_deployment_record(
    client: TestClient, login_as, caigo_admin
) -> None:
    row_id = make_system(client)
    reach_validation(client, row_id)

    body = lifecycle(client, row_id)
    assert requirement(body, "validation_report")["satisfied"] is False
    assert requirement(body, "deployment_approved")["satisfied"] is False
    assert requirement(body, "deployment_record")["satisfied"] is False
    # No high risks were added, so that requirement passes from the start.
    assert requirement(body, "no_untreated_high_risks")["satisfied"] is True

    upload(client, row_id, "validation_report")
    client.put(
        LIFECYCLE.format(row_id=row_id) + "/deployment-record",
        json={
            "deployment_environment": "production",
            "deployment_version": "1.4.0",
            "deployed_at": "2026-09-01",
        },
    )
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")
    login_as(caigo_admin)
    client.post(LIFECYCLE.format(row_id=row_id) + "/approve-deployment")

    assert advance(client, row_id).json()["current_stage"] == "deployment"


def test_the_requester_cannot_approve_their_own_release(
    client: TestClient, db_session: Session, test_user, second_user, make_caigo
) -> None:
    # A backup approver exists so the request itself is allowed (see
    # test_cannot_request_deployment_approval_when_you_are_the_only_possible_approver
    # for that guard on its own) -- this test is about the separate rule
    # that the requester still can't approve their own release regardless.
    make_caigo(test_user)
    governance_role_service.delegate_caigo(
        db_session, second_user.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )
    row_id = make_system(client)
    reach_validation(client, row_id)
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-deployment")

    assert response.status_code == 409
    # Phrased for whoever is looking at the screen, not the internal entity type.
    assert "someone else has to approve it" in response.text


def test_cannot_request_deployment_approval_when_you_are_the_only_possible_approver(
    client: TestClient, test_user, make_caigo
) -> None:
    make_caigo(test_user)
    row_id = make_system(client)
    reach_validation(client, row_id)

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")

    assert response.status_code == 400
    assert "backup approver" in response.json()["detail"]


def test_non_caigo_admin_cannot_approve_a_release(
    client: TestClient, make_user, login_as
) -> None:
    row_id = make_system(client)
    reach_validation(client, row_id)
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")
    login_as(make_user(role=UserRole.ADMIN))

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-deployment")

    assert response.status_code == 403


def test_approving_a_release_requires_the_approve_permission(
    client: TestClient, make_user, login_as
) -> None:
    row_id = make_system(client)
    reach_validation(client, row_id)
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-deployment")

    assert response.status_code == 403


# --- Deployment ------------------------------------------------------------


def reach_deployment(client: TestClient, row_id: int, login_as, caigo_admin) -> None:
    reach_validation(client, row_id)
    upload(client, row_id, "validation_report")
    client.put(
        LIFECYCLE.format(row_id=row_id) + "/deployment-record",
        json={
            "deployment_environment": "production",
            "deployment_version": "1.4.0",
            "deployed_at": "2026-09-01",
        },
    )
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")
    login_as(caigo_admin)
    client.post(LIFECYCLE.format(row_id=row_id) + "/approve-deployment")
    advance(client, row_id)


def test_deployment_gate_requires_monitoring_setup(
    client: TestClient, login_as, caigo_admin
) -> None:
    row_id = make_system(client)
    reach_deployment(client, row_id, login_as, caigo_admin)

    body = lifecycle(client, row_id)
    assert body["current_stage"] == "deployment"
    assert requirement(body, "monitoring_plan")["satisfied"] is False
    assert requirement(body, "monitoring_owner")["satisfied"] is False
    assert requirement(body, "incident_escalation_path")["satisfied"] is False
    # Both assessments were completed moments ago, so reviews are current.
    assert requirement(body, "reviews_current")["satisfied"] is True

    upload(client, row_id, "monitoring_plan")
    client.put(
        LIFECYCLE.format(row_id=row_id) + "/monitoring",
        json={"monitoring_owner_id": 1, "incident_escalation_path": "Page the ML on-call."},
    )

    assert advance(client, row_id).json()["current_stage"] == "operation_and_monitoring"


def test_owner_can_be_set_and_cleared(client: TestClient) -> None:
    row_id = make_system(client)

    response = client.put(LIFECYCLE.format(row_id=row_id) + "/owner", json={"owner_id": 1})
    assert response.status_code == 200
    assert response.json()["owner_id"] == 1

    response = client.put(LIFECYCLE.format(row_id=row_id) + "/owner", json={"owner_id": None})
    assert response.json()["owner_id"] is None


# --- Reverting -------------------------------------------------------------


def test_reverting_needs_a_reason_and_steps_back_one_stage(client: TestClient) -> None:
    row_id = make_system(client)
    pass_inception(client, row_id)
    advance(client, row_id)

    assert (
        client.post(LIFECYCLE.format(row_id=row_id) + "/revert", json={"reason": "  "}).status_code
        == 400
    )

    response = client.post(
        LIFECYCLE.format(row_id=row_id) + "/revert", json={"reason": "Scope changed"}
    )

    assert response.status_code == 200
    assert response.json()["current_stage"] == "inception"


def test_reverting_out_of_deployment_clears_the_release_approval(
    client: TestClient, login_as, caigo_admin
) -> None:
    """A stale approval must not carry a system back over the gate."""
    row_id = make_system(client)
    reach_deployment(client, row_id, login_as, caigo_admin)
    assert lifecycle(client, row_id)["deployment_approved_by"] is not None

    body = client.post(
        LIFECYCLE.format(row_id=row_id) + "/revert", json={"reason": "Rollback"}
    ).json()

    assert body["current_stage"] == "verification_and_validation"
    assert body["deployment_approved_by"] is None
    assert requirement(body, "deployment_approved")["satisfied"] is False


def test_cannot_revert_out_of_the_first_stage(client: TestClient) -> None:
    row_id = make_system(client)

    response = client.post(
        LIFECYCLE.format(row_id=row_id) + "/revert", json={"reason": "n/a"}
    )

    assert response.status_code == 409


# --- Inventory coupling ----------------------------------------------------


def test_the_stage_cell_cannot_be_hand_edited_in_the_grid(client: TestClient) -> None:
    row_id = make_system(client)

    client.put(
        f"/api/v1/ai-system-inventory/rows/{row_id}",
        json={"data": {"lifecycle_stage": "deployment", "risk_tier": "limited"}},
    )

    row = client.get("/api/v1/ai-system-inventory").json()["rows"][0]
    assert row["data"]["lifecycle_stage"] == "inception"
    assert row["data"]["risk_tier"] == "limited"


def test_advancing_updates_the_inventory_cell(client: TestClient) -> None:
    row_id = make_system(client)
    pass_inception(client, row_id)
    advance(client, row_id)

    row = client.get("/api/v1/ai-system-inventory").json()["rows"][0]
    assert row["data"]["lifecycle_stage"] == "design"


def test_deleting_an_ai_system_removes_its_lifecycle(client: TestClient) -> None:
    row_id = make_system(client)
    assert client.delete(f"/api/v1/ai-system-inventory/rows/{row_id}").status_code == 204

    assert client.get(LIFECYCLE.format(row_id=row_id)).status_code == 404
