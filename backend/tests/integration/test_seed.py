from sqlalchemy.orm import Session

from app.repositories import (
    policy_repository,
    procedure_repository,
    risk_assessment_repository,
)
from app.seed import seed
from app.services import ai_system_inventory_service, risk_assessment_service


def test_seed_populates_all_pillars(db_session: Session) -> None:
    seed(db_session)

    policies = policy_repository.list_all(db_session)
    procedures = procedure_repository.list_all(db_session)
    ai_system_rows = ai_system_inventory_service.list_rows(db_session)
    risk_assessments = risk_assessment_repository.list_all(db_session)

    assert len(policies) == 2
    assert len(procedures) == 2
    assert len(ai_system_rows) == 3
    assert len(risk_assessments) == 2

    total_risk_items = sum(
        len(risk_assessment_service.list_rows(db_session, ra.id)) for ra in risk_assessments
    )
    assert total_risk_items == 3


def test_seed_creates_an_approved_policy_with_a_document(db_session: Session) -> None:
    seed(db_session)

    policies = policy_repository.list_all(db_session)
    approved = next(p for p in policies if p.title == "Data Retention Policy")

    assert approved.status == "approved"
    assert approved.version == 2  # bumped once by the seeded document upload


def test_seed_is_idempotent(db_session: Session) -> None:
    seed(db_session)
    seed(db_session)

    policies = policy_repository.list_all(db_session)

    assert len(policies) == 2
