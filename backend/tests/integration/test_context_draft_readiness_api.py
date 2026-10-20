"""What the organization-context draft would read, counted before anyone asks for one."""

from fastapi.testclient import TestClient

from app.models.user import User

URL = "/api/v1/organization-context/ai-draft/readiness"


def counts(client: TestClient) -> dict[str, int]:
    response = client.get(URL)
    assert response.status_code == 200, response.text
    return {item["key"]: item["count"] for item in response.json()}


def test_an_empty_platform_has_nothing_for_a_draft_to_read(
    client: TestClient, test_user: User
) -> None:
    body = client.get(URL).json()

    assert [item["key"] for item in body] == [
        "ai_systems",
        "policies",
        "procedures",
        "ai_tools",
        "suppliers",
    ]
    assert all(item["count"] == 0 for item in body)
    # Each says where to add it and what the draft cannot do without it.
    assert [item["href"] for item in body] == [
        "/ai-systems",
        "/policies",
        "/procedures",
        "/ai-tools",
        "/suppliers",
    ]
    assert all(item["empty_note"].startswith("It cannot") for item in body)


def test_the_counts_follow_what_the_draft_would_actually_read(
    client: TestClient, test_user: User, db_session
) -> None:
    from app.models.ai_tool import AITool, AIToolStatus
    from app.models.policy import Policy
    from app.models.supplier import Supplier, SupplierStatus

    db_session.add_all(
        [
            Policy(title="AI Policy", description="Sets the rules."),
            Policy(title="No description"),  # nothing for a draft to read
            AITool(name="ChatGPT", domains=["chatgpt.com"], status=AIToolStatus.APPROVED),
            AITool(name="Known only", domains=["k.example"], status=AIToolStatus.CATALOGUED),
            Supplier(name="OpenAI", supplier_type="model_provider", status=SupplierStatus.ACTIVE),
            Supplier(name="Old", supplier_type="other", status=SupplierStatus.INACTIVE),
        ]
    )
    db_session.commit()
    added = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "purpose": "Ranks applicants."}},
    )
    assert added.status_code == 201, added.text

    found = counts(client)

    assert found["ai_systems"] == 1
    assert found["policies"] == 1
    assert found["ai_tools"] == 1
    assert found["suppliers"] == 1
    assert found["procedures"] == 0
