"""Populate the local database with realistic demo data.

Run from backend/ with the venv active:

    python -m app.seed

Goes through the real service layer (not raw inserts) so every
create/status-change/upload is audit-logged exactly like a real user
action, and skips entirely if the database already has policies in it
-- safe to run again without duplicating data.
"""

from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories import framework_control_repository, policy_repository
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    evidence_service,
    framework_service,
    policy_service,
    procedure_service,
    risk_assessment_service,
)


def _tag(db: Session, entity_type: str, entity_id: int, *codes: str) -> None:
    """codes like 'iso_42001:8.4' or 'eu_ai_act:Art.9'."""
    controls = {
        f"{c.framework}:{c.code}": c.id for c in framework_control_repository.list_all(db)
    }
    control_ids = [controls[code] for code in codes]
    framework_service.set_tags(db, entity_type, entity_id, control_ids, actor_id=None)


def _fake_upload(filename: str, content: bytes) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, content_type="application/pdf", file=BytesIO(content))


def seed(db: Session) -> None:
    if policy_repository.list_all(db):
        print("Database already has data -- skipping seed.")
        return

    print("Seeding policies...")
    retention_policy = policy_service.create_policy(
        db,
        PolicyCreate(
            title="Data Retention Policy",
            description="Governs how long personal and model data may be retained.",
        ),
        actor_id=None,
    )
    evidence_service.upload_evidence(
        db,
        "Policy",
        retention_policy.id,
        None,
        _fake_upload("data-retention-policy-v1.pdf", b"Demo signed policy document."),
        "Signed policy document",
        actor_id=None,
    )
    policy_service.submit_for_review(db, retention_policy.id, actor_id=None)
    policy_service.approve_policy(db, retention_policy.id, actor_id=None)
    _tag(db, "Policy", retention_policy.id, "eu_ai_act:Art.10")

    vendor_policy = policy_service.create_policy(
        db,
        PolicyCreate(
            title="Vendor AI Risk Policy",
            description="Requirements for assessing third-party AI vendors before procurement.",
        ),
        actor_id=None,
    )
    policy_service.submit_for_review(db, vendor_policy.id, actor_id=None)
    _tag(db, "Policy", vendor_policy.id, "iso_42001:6.1", "eu_ai_act:Art.9")

    print("Seeding procedures...")
    validation_procedure = procedure_service.create_procedure(
        db,
        ProcedureCreate(
            title="Model Validation Procedure",
            description="Steps required before a model can move from staging to production.",
            policy_id=vendor_policy.id,
        ),
        actor_id=None,
    )
    procedure_service.submit_for_review(db, validation_procedure.id, actor_id=None)
    procedure_service.approve_procedure(db, validation_procedure.id, actor_id=None)

    procedure_service.create_procedure(
        db,
        ProcedureCreate(
            title="AI Incident Response Procedure",
            description="Escalation path when a deployed AI system causes or risks harm.",
        ),
        actor_id=None,
    )

    print("Seeding AI System Inventory...")
    resume_screener = ai_system_inventory_service.add_row(
        db,
        {
            "name": "Resume Screener",
            "description": "Ranks incoming job applications for recruiters.",
            "purpose": "Filter job applicants",
            "lifecycle_stage": "deployed",
            "risk_tier": "high",
        },
        actor_id=None,
    )
    ai_system_inventory_service.add_row(
        db,
        {
            "name": "Customer Support Chatbot",
            "description": "Answers common customer questions on the support site.",
            "purpose": "Customer self-service",
            "lifecycle_stage": "deployed",
            "risk_tier": "limited",
        },
        actor_id=None,
    )
    fraud_model = ai_system_inventory_service.add_row(
        db,
        {
            "name": "Fraud Detection Model",
            "description": "Flags potentially fraudulent transactions for manual review.",
            "purpose": "Transaction fraud scoring",
            "lifecycle_stage": "testing",
            "risk_tier": "high",
        },
        actor_id=None,
    )

    print("Seeding risk assessments...")
    resume_assessment = risk_assessment_service.create_risk_assessment(
        db,
        RiskAssessmentCreate(ai_system_row_id=resume_screener.id),
        actor_id=None,
    )
    _tag(db, "RiskAssessment", resume_assessment.id, "iso_42001:8.4", "eu_ai_act:Art.9")
    risk_assessment_service.add_row(
        db,
        resume_assessment.id,
        {
            "category": "Bias",
            "description": "Model may rank candidates unevenly across demographic groups.",
            "likelihood": 4,
            "impact": 4,
            "mitigation": "Add fairness testing to the validation pipeline.",
            "residual_likelihood": 2,
            "residual_impact": 2,
            "risk_owner": "ML Team",
            "treatment_deadline": str(date.today() - timedelta(days=10)),
            "status": "open",
        },
        actor_id=None,
    )
    risk_assessment_service.add_row(
        db,
        resume_assessment.id,
        {
            "category": "Transparency",
            "description": "Candidates are not informed an AI system screens their application.",
            "likelihood": 2,
            "impact": 3,
            "mitigation": "Add a disclosure notice to the application flow.",
            "residual_likelihood": 1,
            "residual_impact": 2,
            "risk_owner": "Legal",
            "treatment_deadline": str(date.today() - timedelta(days=5)),
            "status": "treated",
        },
        actor_id=None,
    )

    fraud_assessment = risk_assessment_service.create_risk_assessment(
        db,
        RiskAssessmentCreate(ai_system_row_id=fraud_model.id),
        actor_id=None,
    )
    _tag(db, "RiskAssessment", fraud_assessment.id, "iso_42001:6.1")
    risk_assessment_service.add_row(
        db,
        fraud_assessment.id,
        {
            "category": "Fairness",
            "description": "Model may flag transactions from certain regions more often.",
            "likelihood": 5,
            "impact": 5,
            "mitigation": "Under review with the model risk committee.",
            "risk_owner": "Risk Team",
            "treatment_deadline": str(date.today() + timedelta(days=30)),
            "status": "in_progress",
        },
        actor_id=None,
    )

    print("Seed complete.")


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
