"""The chat assistant over HTTP: who may use it, and whose conversations they reach."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.user import UserRole

BASE = "/api/v1/assistant/conversations"


def fake_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def configure(client: TestClient) -> None:
    client.put(
        "/api/v1/ai-assist/settings",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "sk-test"},
    )


def test_a_viewer_can_use_the_assistant(client: TestClient, make_user, login_as) -> None:
    """The assistant reads and answers; it changes nothing. The people with
    the most questions about a record are often the ones who can only view
    it, so the gate is being signed in, not holding edit rights."""
    configure(client)
    login_as(make_user(role=UserRole.VIEWER))

    conversation = client.post(BASE, json={}).json()
    with patch("litellm.completion", return_value=fake_response("The records don't say.")):
        answer = client.post(
            f"{BASE}/{conversation['id']}/messages", json={"question": "What is our policy?"}
        )

    assert answer.status_code == 200
    assert answer.json()["role"] == "assistant"


def test_the_assistant_is_closed_to_anyone_signed_out(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get(BASE).status_code == 401
    assert unauthenticated_client.post(BASE, json={}).status_code == 401


def test_another_persons_conversation_is_not_found_whatever_you_try(
    client: TestClient, make_user, login_as
) -> None:
    configure(client)
    owner = make_user(role=UserRole.CONTRIBUTOR)
    login_as(owner)
    conversation_id = client.post(BASE, json={}).json()["id"]

    login_as(make_user(role=UserRole.ADMIN))

    # Not even an admin: there is no administrative view of someone's chats.
    assert client.get(f"{BASE}/{conversation_id}").status_code == 404
    assert (
        client.post(f"{BASE}/{conversation_id}/messages", json={"question": "hello"}).status_code
        == 404
    )
    assert client.delete(f"{BASE}/{conversation_id}").status_code == 404
    assert client.get(BASE).json() == []


def test_a_conversation_comes_back_with_its_messages_and_citations(client: TestClient) -> None:
    configure(client)
    policy = client.post(
        "/api/v1/policies",
        json={"title": "Data Retention Policy", "description": "Applicant data is kept 24 months."},
    ).json()
    conversation_id = client.post(BASE, json={}).json()["id"]

    with patch(
        "litellm.completion", return_value=fake_response("Kept for 24 months [S1].")
    ):
        client.post(
            f"{BASE}/{conversation_id}/messages",
            json={"question": "How long is applicant data kept?"},
        )

    detail = client.get(f"{BASE}/{conversation_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    citation = detail["messages"][1]["citations"][0]
    assert citation["href"] == f"/policies/{policy['id']}"
    assert citation["title"] == "Policy: Data Retention Policy"


def test_asking_with_no_provider_configured_is_a_clear_503(client: TestClient) -> None:
    conversation_id = client.post(BASE, json={}).json()["id"]

    response = client.post(f"{BASE}/{conversation_id}/messages", json={"question": "hello"})

    assert response.status_code == 503
    assert "isn't set up" in response.text


def test_a_conversation_can_be_opened_on_a_record(client: TestClient) -> None:
    response = client.post(BASE, json={"context_entity_type": "Policy", "context_entity_id": 3})

    assert response.status_code == 201
    assert response.json()["context_entity_type"] == "Policy"


def test_an_unknown_record_type_is_refused(client: TestClient) -> None:
    response = client.post(
        BASE, json={"context_entity_type": "Spaceship", "context_entity_id": 3}
    )

    assert response.status_code == 400


def test_deleting_a_conversation(client: TestClient) -> None:
    conversation_id = client.post(BASE, json={}).json()["id"]

    assert client.delete(f"{BASE}/{conversation_id}").status_code == 204
    assert client.get(f"{BASE}/{conversation_id}").status_code == 404


def test_warming_starts_in_the_background_and_returns_at_once(client: TestClient) -> None:
    with patch("app.core.embeddings.warm") as warm:
        response = client.post("/api/v1/assistant/warm")

    assert response.status_code == 202
    warm.assert_called_once()
