"""Shared test helpers.

Risk assessments require a completed impact assessment for the AI system
first (ISO 42001 sequences 8.4 before the risk work, and
risk_assessment_service enforces it), so most risk-assessment tests need to
satisfy that precondition before they can get to what they actually test.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.services import impact_assessment_service


def complete_impact_assessment(client: TestClient, ai_system_row_id: int) -> dict:
    """API path: creates and completes an impact assessment for the system."""
    created = client.post(
        "/api/v1/impact-assessments",
        json={"ai_system_row_id": ai_system_row_id},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    completed = client.put(
        f"/api/v1/impact-assessments/{body['id']}", json={"status": "completed"}
    )
    assert completed.status_code == 200, completed.text
    return completed.json()


def complete_impact_assessment_db(db: Session, ai_system_row_id: int) -> int:
    """Service path, for tests that work against db_session directly."""
    assessment = impact_assessment_service.create_for_ai_system(
        db, ai_system_row_id, ImpactAssessmentCreate(), actor_id=None
    )
    impact_assessment_service.update(
        db, assessment.id, ImpactAssessmentUpdate(status="completed"), actor_id=None
    )
    return assessment.id
