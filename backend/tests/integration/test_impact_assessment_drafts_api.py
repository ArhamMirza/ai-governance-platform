"""AI drafts of an impact assessment, over HTTP."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import complete_impact_assessment
from tests.unit.test_impact_assessment_drafting import FakeDrafter


def configure(client: TestClient) -> None:
    client.put(
        "/api/v1/ai-assist/settings",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "sk-test"},
    )


def make_assessment(client: TestClient) -> int:
    row = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "purpose": "Ranks job applicants by fit."}},
    ).json()
    return complete_impact_assessment(client, row["id"])["id"]


def test_draft_review_and_apply_round_trip(client: TestClient) -> None:
    configure(client)
    assessment_id = make_assessment(client)
    base = f"/api/v1/impact-assessments/{assessment_id}/ai-drafts"

    with patch("litellm.completion", side_effect=FakeDrafter()):
        created = client.post(base)
    assert created.status_code == 201
    draft = created.json()

    latest = client.get(f"{base}/latest").json()
    assert latest["id"] == draft["id"]
    purpose = next(p for p in draft["proposals"] if p["key"] == "narrative.intended_purpose")
    assert draft["sources"][0]["n"] == 1

    applied = client.post(
        f"{base}/{draft['id']}/apply",
        json={"accepted": [{"key": purpose["key"], "value": "Edited by the assessor."}]},
    )

    assert applied.status_code == 200
    assert applied.json()["intended_purpose"] == "Edited by the assessor."
    # Nothing left waiting once it has been decided.
    assert client.get(f"{base}/latest").json() is None


def test_a_viewer_can_neither_request_nor_apply_a_draft(
    client: TestClient, make_user, login_as
) -> None:
    """A draft exists to be written into the record, so it takes edit rights,
    the same as typing into the form."""
    configure(client)
    assessment_id = make_assessment(client)
    base = f"/api/v1/impact-assessments/{assessment_id}/ai-drafts"
    with patch("litellm.completion", side_effect=FakeDrafter()):
        draft_id = client.post(base).json()["id"]

    login_as(make_user(role=UserRole.VIEWER))

    with patch("litellm.completion", side_effect=FakeDrafter()) as completion:
        assert client.post(base).status_code == 403
        assert completion.call_count == 0
    assert client.get(f"{base}/latest").status_code == 403
    assert (
        client.post(f"{base}/{draft_id}/apply", json={"accepted": []}).status_code == 403
    )
    assert client.post(f"{base}/{draft_id}/discard").status_code == 403


def test_applying_a_draft_twice_is_a_conflict(client: TestClient) -> None:
    configure(client)
    assessment_id = make_assessment(client)
    base = f"/api/v1/impact-assessments/{assessment_id}/ai-drafts"
    with patch("litellm.completion", side_effect=FakeDrafter()):
        draft = client.post(base).json()
    body = {"accepted": [{"key": "narrative.conclusion", "value": "Moderate overall impact."}]}

    assert client.post(f"{base}/{draft['id']}/apply", json=body).status_code == 200
    assert client.post(f"{base}/{draft['id']}/apply", json=body).status_code == 409


def test_discarding_a_draft(client: TestClient) -> None:
    configure(client)
    assessment_id = make_assessment(client)
    base = f"/api/v1/impact-assessments/{assessment_id}/ai-drafts"
    with patch("litellm.completion", side_effect=FakeDrafter()):
        draft_id = client.post(base).json()["id"]

    assert client.post(f"{base}/{draft_id}/discard").status_code == 204
    assert client.get(f"{base}/latest").json() is None


def test_drafting_with_no_provider_configured_is_a_clear_503(client: TestClient) -> None:
    assessment_id = make_assessment(client)

    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/ai-drafts")

    assert response.status_code == 503
