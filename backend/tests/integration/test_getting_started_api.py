"""The getting-started checklist: worked out from the records, never stored."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ai_tool import AITool, AIToolStatus
from app.models.eu_ai_act_applicability import EuAiActApplicability
from app.models.governance_role import GovernanceRole
from app.models.impact_assessment import ImpactAssessment
from app.models.policy import Policy, PolicyStatus
from app.models.supplier import Supplier, SupplierStatus
from app.models.user import User, UserRole
from app.schemas.ai_assist import AiAssistSettingsUpdate
from app.services import (
    ai_assist_service,
    ai_system_inventory_service,
    governance_role_service,
    organization_context_service,
)

URL = "/api/v1/dashboard/getting-started"
KEYS = [
    "organization",
    "roles",
    "people",
    "ai_systems",
    "eu_scope",
    "policies",
    "tools",
    "suppliers",
    "assessment",
    "assistant",
]


def checklist(client: TestClient) -> dict:
    response = client.get(URL)
    assert response.status_code == 200, response.text
    return response.json()


def done(client: TestClient) -> dict[str, bool]:
    return {s["key"]: s["done"] for s in checklist(client)["steps"]}


def test_a_new_installation_has_everything_to_do_in_the_order_to_do_it(
    client: TestClient, test_user: User
) -> None:
    body = checklist(client)

    assert [s["key"] for s in body["steps"]] == KEYS
    assert body["done_count"] == 0 and body["total"] == len(KEYS)
    assert body["complete"] is False
    assert body["next_key"] == "organization"
    assert [s["optional"] for s in body["steps"]] == [False] * 9 + [True]
    # Each step says why, and where to do it.
    assert all(s["why"] and s["href"].startswith("/") for s in body["steps"])


def test_each_step_is_done_when_its_records_exist(
    client: TestClient, test_user: User, db_session: Session, make_user
) -> None:
    db = db_session

    organization_context_service.update(
        db, {"organization_description": "A small recruiter using AI to screen CVs."}, None
    )
    caigo = db.query(GovernanceRole).filter_by(name="Chief AI Governance Officer").one()
    governance_role_service.assign_user(db, caigo.id, test_user.id, actor_id=None)
    make_user(role=UserRole.CONTRIBUTOR)
    row = ai_system_inventory_service.add_row(db, {"name": "Screener"}, actor_id=None)
    db.add(EuAiActApplicability(in_scope=True, has_high_risk_systems=False))
    db.add(Policy(title="AI Policy", status=PolicyStatus.DRAFT))
    db.add(AITool(name="ChatGPT", domains=["chatgpt.com"], status=AIToolStatus.APPROVED))
    db.add(Supplier(name="OpenAI", supplier_type="model_provider", status=SupplierStatus.ACTIVE))
    db.add(ImpactAssessment(ai_system_row_id=row.id))
    db.commit()

    after = done(client)
    assert all(after[key] for key in KEYS[:-1]), after
    assert after["assistant"] is False  # optional, and not set up
    body = checklist(client)
    assert body["complete"] is True and body["next_key"] is None
    assert body["done_count"] == 9


def test_the_next_step_moves_on_as_each_one_is_done(
    client: TestClient, test_user: User, db_session: Session
) -> None:
    assert checklist(client)["next_key"] == "organization"

    organization_context_service.update(db_session, {"organization_description": "x"}, None)
    assert checklist(client)["next_key"] == "roles"

    caigo = db_session.query(GovernanceRole).filter_by(name="Chief AI Governance Officer").one()
    governance_role_service.assign_user(db_session, caigo.id, test_user.id, actor_id=None)
    assert checklist(client)["next_key"] == "people"


def test_turning_on_the_assistant_ticks_the_optional_step(
    client: TestClient, test_user: User, db_session: Session
) -> None:
    ai_assist_service.update_settings(
        db_session,
        AiAssistSettingsUpdate(
            provider="anthropic",
            model="claude-sonnet-5",
            api_key="sk-test",
            daily_token_budget=1000,
        ),
        actor_id=None,
    )

    assert done(client)["assistant"] is True


@pytest.mark.parametrize(
    ("step", "record"),
    [
        (
            "organization",
            lambda db, u: organization_context_service.update(
                db, {"organization_description": "   "}, None
            ),
        ),
        ("eu_scope", lambda db, u: db.add(EuAiActApplicability(in_scope=None))),
        ("policies", lambda db, u: db.add(Policy(title="Old", status=PolicyStatus.RETIRED))),
        (
            "tools",
            lambda db, u: db.add(
                AITool(name="Known", domains=["k.example"], status=AIToolStatus.CATALOGUED)
            ),
        ),
        (
            "suppliers",
            lambda db, u: db.add(
                Supplier(name="Gone", supplier_type="other", status=SupplierStatus.INACTIVE)
            ),
        ),
    ],
)
def test_a_record_that_does_not_really_count_does_not_tick_the_step(
    client: TestClient, test_user: User, db_session: Session, step: str, record
) -> None:
    record(db_session, test_user)
    db_session.commit()

    assert done(client)[step] is False


def test_a_deactivated_person_does_not_count_as_someone_added(
    client: TestClient, test_user: User, db_session: Session, make_user
) -> None:
    make_user(role=UserRole.CONTRIBUTOR, is_active=False)

    assert done(client)["people"] is False


def test_a_stranger_cannot_read_it(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get(URL).status_code == 401


def test_an_employee_login_cannot_read_it(
    client: TestClient, test_user: User, make_user, login_as
) -> None:
    login_as(make_user(role=UserRole.EMPLOYEE))

    assert client.get(URL).status_code == 403
