"""The AI assistance endpoints: who can reach them, and what they give back."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import complete_impact_assessment

SETTINGS = "/api/v1/ai-assist/settings"
STATUS = "/api/v1/ai-assist/status"
DRAFT = "/api/v1/ai-assist/draft"


def fake_response(text: str = "Drafted."):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def configure(client: TestClient, **overrides):
    body = {
        "provider": "anthropic",
        "model": "claude-sonnet-5",
        "api_key": "sk-test-secret",
        "daily_token_budget": 200000,
    }
    body.update(overrides)
    return client.put(SETTINGS, json=body)


def make_assessment(client: TestClient) -> int:
    row = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "purpose": "Rank applicants"}},
    ).json()
    return complete_impact_assessment(client, row["id"])["id"]


# ---------- status ----------


def test_status_says_ai_is_off_before_anything_is_configured(client: TestClient) -> None:
    body = client.get(STATUS).json()

    assert body["available"] is False
    assert body["reason"]


def test_any_signed_in_user_can_read_status(client: TestClient, make_user, login_as) -> None:
    """The UI has to know whether to offer AI at all, and status carries no
    credential -- only whether one exists."""
    login_as(make_user(role=UserRole.VIEWER))

    assert client.get(STATUS).status_code == 200


def test_status_is_refused_when_signed_out(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get(STATUS).status_code == 401


# ---------- settings ----------


def test_an_admin_configures_the_provider(client: TestClient) -> None:
    response = configure(client)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "anthropic"
    assert body["has_api_key"] is True
    assert client.get(STATUS).json()["available"] is True


def test_the_api_key_is_never_returned_by_the_api(client: TestClient) -> None:
    configure(client, api_key="sk-super-secret")

    assert "sk-super-secret" not in client.get(SETTINGS).text
    assert "sk-super-secret" not in client.put(
        SETTINGS, json={"provider": "anthropic", "model": "claude-sonnet-5"}
    ).text


def test_a_contributor_cannot_read_or_change_the_provider(
    client: TestClient, make_user, login_as
) -> None:
    """The provider setting carries an organizational credential and its
    spend, so it sits behind the same admin gate as risk criteria."""
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    assert client.get(SETTINGS).status_code == 403
    assert configure(client).status_code == 403


def test_a_self_hosted_provider_needs_its_url(client: TestClient) -> None:
    response = client.put(
        SETTINGS, json={"provider": "local", "model": "llama3.3"}
    )

    assert response.status_code == 400
    assert "URL" in response.text


def test_choosing_a_self_hosted_model_is_reported_as_local(client: TestClient) -> None:
    configure(
        client, provider="local", model="llama3.3", base_url="http://localhost:11434"
    )

    body = client.get(STATUS).json()
    assert body["available"] is True
    # What the settings page uses to state plainly that nothing leaves the
    # deployment on this provider.
    assert body["is_local"] is True


# ---------- drafting ----------


def test_drafting_returns_text_without_touching_the_record(client: TestClient) -> None:
    configure(client)
    assessment_id = make_assessment(client)
    before = client.get(f"/api/v1/impact-assessments/{assessment_id}").json()

    with patch("litellm.completion", return_value=fake_response("A drafted purpose.")):
        response = client.post(
            DRAFT, json={"kind": "intended_purpose", "impact_assessment_id": assessment_id}
        )

    assert response.status_code == 200
    assert response.json()["draft"] == "A drafted purpose."
    # The draft is text handed back, not a write -- it lands in the box the
    # user types in, and only their save puts it on the record.
    assert client.get(f"/api/v1/impact-assessments/{assessment_id}").json() == before


def test_drafting_needs_edit_rights(client: TestClient, make_user, login_as) -> None:
    configure(client)
    assessment_id = make_assessment(client)
    login_as(make_user(role=UserRole.VIEWER))

    response = client.post(
        DRAFT, json={"kind": "intended_purpose", "impact_assessment_id": assessment_id}
    )

    assert response.status_code == 403


def test_drafting_reports_when_no_provider_is_configured(client: TestClient) -> None:
    assessment_id = make_assessment(client)

    response = client.post(
        DRAFT, json={"kind": "conclusion", "impact_assessment_id": assessment_id}
    )

    assert response.status_code == 503
    assert "isn't set up" in response.text


def test_drafting_an_unknown_field_is_rejected(client: TestClient) -> None:
    configure(client)
    assessment_id = make_assessment(client)

    response = client.post(
        DRAFT, json={"kind": "whatever_i_like", "impact_assessment_id": assessment_id}
    )

    assert response.status_code == 400
