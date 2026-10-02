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
from app.repositories import (
    framework_control_repository,
    governance_role_repository,
    policy_repository,
)
from app.schemas.ai_incident import AIIncidentCreate, AIIncidentUpdate
from app.schemas.competence import CompetenceRequirementCreate
from app.schemas.corrective_action import CorrectiveActionCreate, CorrectiveActionUpdate
from app.schemas.eu_ai_act import EuAiActApplicabilityUpdate
from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.schemas.internal_audit import AuditFindingCreate, AuditProgramCreate, InternalAuditCreate
from app.schemas.management_review import (
    ManagementReviewMeetingCreate,
    ManagementReviewSettingsUpdate,
)
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.schemas.supplier import (
    SupplierAISystemLinkUpdate,
    SupplierCreate,
    SupplierReviewCreate,
    SupplierUpdate,
)
from app.services import (
    ai_incident_service,
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    competence_service,
    corrective_action_service,
    eu_ai_act_service,
    evidence_service,
    framework_service,
    impact_assessment_service,
    internal_audit_service,
    management_review_service,
    policy_service,
    procedure_service,
    risk_assessment_service,
    supplier_service,
)

# Placeholder for "the first account", matching the owner_id=1 stand-in
# _seed_impact_assessment already uses -- the seed creates no users, and
# none of these ids are real FKs.
PLACEHOLDER_USER_ID = 1


def _tag(db: Session, entity_type: str, entity_id: int, *codes: str) -> None:
    """codes like 'iso_42001:8.4' or 'eu_ai_act:Art.9'."""
    controls = {f"{c.framework}:{c.code}": c.id for c in framework_control_repository.list_all(db)}
    control_ids = [controls[code] for code in codes]
    framework_service.set_tags(db, entity_type, entity_id, control_ids, actor_id=None)


def _fake_upload(filename: str, content: bytes) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, content_type="application/pdf", file=BytesIO(content))


def _seed_impact_assessment(
    db: Session,
    ai_system_row_id: int,
    *,
    system_description: str,
    intended_purpose: str,
    foreseeable_misuse: str,
    data_and_model_info: str,
    deployment_environment: str,
    affected_interested_parties: str,
    human_oversight_role: str,
    conclusion: str,
    scores: dict[str, int],
) -> None:
    """Creates a completed impact assessment. Every narrative section and
    all eight factors have to be written up before it can be submitted (see
    impact_assessment_service.missing_content), so `scores` covers them all."""
    # submit_for_owner_approval requires a real owner on the AI system, or
    # the owner stage could never be approved -- this demo data doesn't
    # model a real accountable owner, so it stands in a placeholder id
    # (owner_id isn't a real FK, matching data_owner/risk_owner elsewhere).
    ai_system_lifecycle_service.set_owner(db, ai_system_row_id, owner_id=1, actor_id=None)

    assessment = impact_assessment_service.create_for_ai_system(
        db,
        ai_system_row_id,
        ImpactAssessmentCreate(assessment_date=date.today()),
        actor_id=None,
    )
    for factor, score in scores.items():
        impact_assessment_service.update_factor(
            db,
            assessment.id,
            factor,
            benefits=f"Documented benefits for {factor.lower()}.",
            harms=f"Documented harms for {factor.lower()}.",
            criteria=f"Scored against the organization's {factor.lower()} criteria.",
            score=score,
            actor_id=None,
        )
    impact_assessment_service.update(
        db,
        assessment.id,
        ImpactAssessmentUpdate(
            system_description=system_description,
            intended_purpose=intended_purpose,
            foreseeable_misuse=foreseeable_misuse,
            data_and_model_info=data_and_model_info,
            deployment_environment=deployment_environment,
            affected_interested_parties=affected_interested_parties,
            human_oversight_role=human_oversight_role,
            conclusion=conclusion,
        ),
        actor_id=None,
    )
    impact_assessment_service.submit_for_owner_approval(db, assessment.id, actor_id=None)
    impact_assessment_service.approve_owner_stage(db, assessment.id, actor_id=None)
    impact_assessment_service.approve_caigo_stage(db, assessment.id, actor_id=None)
    _tag(db, "ImpactAssessment", assessment.id, "iso_42001:8.4", "iso_42001:A.5.2")


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
    support_chatbot = ai_system_inventory_service.add_row(
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

    print("Seeding impact assessments...")
    # Impact assessment precedes risk assessment (ISO 42001 clause 8.4), and
    # the service enforces it -- so these must be completed first.
    _seed_impact_assessment(
        db,
        resume_screener.id,
        system_description="Ranks incoming job applications for recruiters.",
        intended_purpose="Shortlist applicants for human review, never to reject outright.",
        foreseeable_misuse="Used as the sole decision-maker with no recruiter review.",
        data_and_model_info="Gradient-boosted ranker trained on five years of hiring outcomes.",
        deployment_environment="Internal recruiting portal, used by the talent acquisition team.",
        affected_interested_parties="Job applicants, recruiters and hiring managers.",
        human_oversight_role="A recruiter reviews every shortlist before anyone is contacted.",
        conclusion="Acceptable with recruiter review and a quarterly bias audit.",
        scores={
            "Accountability": 3,
            "Explainability": 3,
            "Transparency": 2,
            "Fairness": 2,
            "Environmental Impact": 1,
            "Reliability": 3,
            "Privacy": 3,
            "Safety": 2,
        },
    )
    _seed_impact_assessment(
        db,
        fraud_model.id,
        system_description="Flags potentially fraudulent transactions for manual review.",
        intended_purpose="Surface suspicious transactions to the fraud operations team.",
        foreseeable_misuse="Auto-blocking accounts without an analyst confirming the flag.",
        data_and_model_info="Anomaly model trained on labelled historical transactions.",
        deployment_environment="Payments pipeline, scoring transactions in near real time.",
        affected_interested_parties="Account holders, merchants and fraud analysts.",
        human_oversight_role="An analyst confirms every flag before an account is restricted.",
        conclusion="Acceptable while analysts confirm flags; revisit false-positive rates.",
        scores={
            "Accountability": 3,
            "Explainability": 2,
            "Transparency": 3,
            "Fairness": 3,
            "Environmental Impact": 1,
            "Reliability": 3,
            "Privacy": 3,
            "Safety": 4,
        },
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

    print("Seeding EU AI Act applicability...")
    # The demo organization builds its own high-risk systems (Resume
    # Screener) and deploys a vendor's (the chatbot's model).
    eu_ai_act_service.update_settings(
        db,
        EuAiActApplicabilityUpdate(
            in_scope=True,
            is_provider=True,
            is_deployer=True,
            has_high_risk_systems=True,
        ),
        actor_id=None,
    )

    _seed_internal_audits(db)
    _seed_management_review(db)
    _seed_incidents(db, support_chatbot.id, fraud_model.id, resume_screener.id)
    _seed_competence(db)
    _seed_suppliers(
        db, resume_screener.id, fraud_model.id, support_chatbot.id, resume_assessment.id
    )

    print("Seed complete.")


def _seed_internal_audits(db: Session) -> None:
    """A recurring program with last month's audit done -- one nonconformity
    raised as a corrective action -- and an ad-hoc program with an audit
    still to come."""
    print("Seeding internal audits...")
    today = date.today()
    annual = internal_audit_service.create_audit_program(
        db,
        AuditProgramCreate(
            title="Annual AI Management System Audit",
            description="Full-scope audit of the AIMS against ISO/IEC 42001 Clauses 4-10.",
            schedule_type="interval",
            interval_months=12,
            start_date=today - timedelta(days=400),
            owner_id=PLACEHOLDER_USER_ID,
        ),
        actor_id=None,
    )
    _tag(db, "AuditProgram", annual.id, "iso_42001:9.2")
    audit = internal_audit_service.create_internal_audit(
        db,
        annual.id,
        InternalAuditCreate(
            title="2026 AIMS audit",
            planned_date=today - timedelta(days=35),
            auditor_id=PLACEHOLDER_USER_ID,
            scope="Risk and impact assessment processes; model validation; AI policy.",
        ),
        actor_id=None,
    )
    nonconformity = internal_audit_service.create_finding(
        db,
        annual.id,
        audit.id,
        AuditFindingCreate(
            description=(
                "The Model Validation Procedure requires fairness testing, but the "
                "Resume Screener's last release shipped without it."
            ),
            finding_type="nonconformity",
        ),
        actor_id=None,
    )
    internal_audit_service.create_finding(
        db,
        annual.id,
        audit.id,
        AuditFindingCreate(
            description="Risk owners are named by team rather than by person.",
            finding_type="observation",
        ),
        actor_id=None,
    )
    internal_audit_service.complete_internal_audit(
        db,
        annual.id,
        audit.id,
        actor_id=None,
        conducted_date=today - timedelta(days=30),
        conclusion="AIMS broadly effective; one nonconformity in model validation.",
    )

    fairness_fix = corrective_action_service.create_corrective_action(
        db,
        CorrectiveActionCreate(
            title="Enforce fairness testing before release",
            nonconformity_description=nonconformity.description,
            root_cause="Fairness testing was a manual step with no release gate checking it.",
            source_type="AuditFinding",
            source_id=nonconformity.id,
            assignee_id=PLACEHOLDER_USER_ID,
            due_date=today + timedelta(days=21),
        ),
        actor_id=None,
    )
    corrective_action_service.update_corrective_action(
        db, fairness_fix.id, CorrectiveActionUpdate(status="in_progress"), actor_id=None
    )
    _tag(db, "CorrectiveAction", fairness_fix.id, "iso_42001:10.2")

    supplier_audit_program = internal_audit_service.create_audit_program(
        db,
        AuditProgramCreate(
            title="Third-Party AI Controls Audit",
            description="Audits of supplier controls, run when a supplier changes materially.",
            schedule_type="ad_hoc",
            owner_id=PLACEHOLDER_USER_ID,
        ),
        actor_id=None,
    )
    internal_audit_service.create_internal_audit(
        db,
        supplier_audit_program.id,
        InternalAuditCreate(
            title="Cloud hosting provider controls",
            planned_date=today + timedelta(days=20),
            scope="Access controls and logging for the fraud model's hosting.",
        ),
        actor_id=None,
    )


def _seed_management_review(db: Session) -> None:
    """Yearly reviews, with last month's meeting recorded -- so the next one
    is comfortably in the future."""
    print("Seeding management review...")
    today = date.today()
    management_review_service.update_settings(
        db,
        ManagementReviewSettingsUpdate(interval_months=12, start_date=today - timedelta(days=380)),
        actor_id=None,
    )
    _tag(
        db,
        management_review_service.SETTINGS_ENTITY_TYPE,
        management_review_service.SETTINGS_ENTITY_ID,
        "iso_42001:9.3",
    )
    meeting = management_review_service.create_meeting(
        db,
        ManagementReviewMeetingCreate(
            meeting_date=today - timedelta(days=20),
            chaired_by=PLACEHOLDER_USER_ID,
            attendees="Chief AI Governance Officer, Head of Data Science, Legal, Risk",
            previous_actions_status="All actions from last year's review are closed.",
            context_changes="EU AI Act high-risk obligations now apply to the Resume Screener.",
            performance_summary=(
                "Internal audit found one nonconformity (fairness testing); corrective "
                "action in progress. One AI incident this period, remediated."
            ),
            stakeholder_feedback="Recruiters asked for clearer explanations of rankings.",
            resource_adequacy="One additional ML engineer needed for fairness testing.",
            improvement_opportunities="Automate fairness checks in the release pipeline.",
            decisions_and_actions=(
                "Approved hiring for fairness testing; release gate to be in place "
                "before the next Resume Screener release."
            ),
        ),
        actor_id=None,
    )
    evidence_service.upload_evidence(
        db,
        management_review_service.MEETING_ENTITY_TYPE,
        meeting.id,
        None,
        _fake_upload("management-review-minutes.pdf", b"Demo meeting minutes."),
        "Signed minutes",
        actor_id=None,
    )


def _seed_incidents(
    db: Session, chatbot_row_id: int, fraud_row_id: int, screener_row_id: int
) -> None:
    """One open incident with a corrective action, one serious incident
    reported to the authority in time, and one minor resolved one."""
    print("Seeding AI incidents...")
    today = date.today()
    dosage = ai_incident_service.create_incident(
        db,
        AIIncidentCreate(
            title="Chatbot gave medication dosage advice",
            description="The support chatbot answered a customer's question about dosage.",
            ai_system_row_id=chatbot_row_id,
            detected_on=today - timedelta(days=6),
            severity="high",
            owner_id=PLACEHOLDER_USER_ID,
        ),
        actor_id=None,
    )
    ai_incident_service.update_incident(
        db,
        dosage.id,
        AIIncidentUpdate(
            status="investigating",
            impact_description="One customer; no harm reported.",
            immediate_actions="Added medical topics to the chatbot's refusal list.",
        ),
        actor_id=None,
    )
    guardrails = corrective_action_service.create_corrective_action(
        db,
        CorrectiveActionCreate(
            title="Block medical advice in chatbot guardrails",
            nonconformity_description=dosage.description,
            source_type=ai_incident_service.ENTITY_TYPE,
            source_id=dosage.id,
            assignee_id=PLACEHOLDER_USER_ID,
            due_date=today - timedelta(days=2),
        ),
        actor_id=None,
    )
    _tag(db, "CorrectiveAction", guardrails.id, "iso_42001:10.2")
    _tag(db, ai_incident_service.ENTITY_TYPE, dosage.id, "iso_42001:A.8.4")

    blocked = ai_incident_service.create_incident(
        db,
        AIIncidentCreate(
            title="Legitimate transactions blocked in one region",
            description=(
                "A data pipeline change caused the fraud model to flag most transactions "
                "from one region, and accounts were restricted before analysts reviewed them."
            ),
            ai_system_row_id=fraud_row_id,
            detected_on=today - timedelta(days=25),
            occurred_on=today - timedelta(days=26),
            severity="critical",
            owner_id=PLACEHOLDER_USER_ID,
            is_serious=True,
            serious_category="other",
        ),
        actor_id=None,
    )
    ai_incident_service.update_incident(
        db,
        blocked.id,
        AIIncidentUpdate(
            impact_description="About 1,200 account holders temporarily lost access to funds.",
            immediate_actions="Rolled back the pipeline change and restored the accounts.",
            root_cause="An unvalidated feature change shifted the model's score distribution.",
            authority_notified_on=today - timedelta(days=14),
            authority_reference="MSA-2026-0417",
            status="resolved",
        ),
        actor_id=None,
    )
    _tag(db, ai_incident_service.ENTITY_TYPE, blocked.id, "eu_ai_act:Art.73")

    outage = ai_incident_service.create_incident(
        db,
        AIIncidentCreate(
            title="Ranking outage fell back to unranked list",
            description=(
                "The ranking service timed out for two hours; recruiters saw an unranked list."
            ),
            ai_system_row_id=screener_row_id,
            detected_on=today - timedelta(days=45),
            severity="low",
        ),
        actor_id=None,
    )
    ai_incident_service.update_incident(
        db, outage.id, AIIncidentUpdate(status="resolved"), actor_id=None
    )


def _seed_competence(db: Session) -> None:
    """Requirements only -- the seed creates no user accounts to record
    completions against, so whoever signs up first sees their own gaps."""
    print("Seeding competence requirements...")
    roles = {role.name: role.id for role in governance_role_repository.list_all(db)}
    requirements = [
        CompetenceRequirementCreate(
            title="AI policy awareness",
            description="What the AI policy requires, and each person's part in it (Clause 7.3).",
            refresh_interval_months=12,
        ),
        CompetenceRequirementCreate(
            title="Bias and fairness testing",
            description="Running and interpreting fairness tests before a model release.",
            governance_role_id=roles.get("Implementation Team"),
            refresh_interval_months=24,
        ),
        CompetenceRequirementCreate(
            title="EU AI Act obligations for system owners",
            description="Provider and deployer obligations for high-risk AI systems.",
            governance_role_id=roles.get("AI System Owner"),
        ),
    ]
    for data in requirements:
        requirement = competence_service.create_requirement(db, data, actor_id=None)
        _tag(
            db,
            competence_service.REQUIREMENT_ENTITY_TYPE,
            requirement.id,
            "iso_42001:7.2",
            "iso_42001:7.3",
        )


def _seed_suppliers(
    db: Session,
    screener_row_id: int,
    fraud_row_id: int,
    chatbot_row_id: int,
    screener_assessment_id: int,
) -> None:
    """A supplier whose contract is ending soon, one whose first review is
    overdue, and a former supplier that shouldn't raise any alerts. Northwind
    provides the Resume Screener's base model, which the demo organization
    fine-tunes -- an Art. 25 substantial modification, consistent with its
    EU AI Act assessment recording it as a provider."""
    print("Seeding suppliers...")
    today = date.today()
    models = supplier_service.create_supplier(
        db,
        SupplierCreate(
            name="Northwind Model Labs",
            supplier_type="model_provider",
            description="Foundation model behind the Resume Screener's ranking.",
            owner_id=PLACEHOLDER_USER_ID,
            contact_name="Priya Shah",
            contact_email="partnerships@northwind.example",
            contract_reference="MSA-NW-2024",
            contract_start=today - timedelta(days=700),
            contract_end=today + timedelta(days=20),
            review_interval_months=12,
            first_review_due=today - timedelta(days=400),
        ),
        actor_id=None,
    )
    supplier_service.update_supplier(
        db,
        models.id,
        SupplierUpdate(
            responsibilities=(
                "Northwind: model training, bias evaluation of the base model, security "
                "patches. Us: fine-tuning data, deployment, human review of rankings."
            ),
            requirements="Model cards for every release; 30 days' notice of model changes.",
        ),
        actor_id=None,
    )
    supplier_service.set_ai_systems(db, models.id, [screener_row_id], actor_id=None)
    supplier_service.update_link(
        db,
        models.id,
        screener_row_id,
        SupplierAISystemLinkUpdate(supplier_role="provider", substantially_modified=True),
        actor_id=None,
    )
    risk_assessment_service.add_row(
        db,
        screener_assessment_id,
        {
            "category": "Third party",
            "description": "Northwind changes the base model without the agreed notice.",
            "likelihood": 2,
            "impact": 4,
            "mitigation": "Contractual 30-day notice; re-run validation on every model change.",
            "risk_owner": "ML Team",
            "supplier_id": str(models.id),
            "treatment_deadline": str(today + timedelta(days=45)),
            "status": "in_progress",
        },
        actor_id=None,
    )
    supplier_service.record_review(
        db,
        models.id,
        SupplierReviewCreate(
            review_date=today - timedelta(days=35),
            outcome="satisfactory",
            notes="Model card and bias evaluation received for the latest release.",
        ),
        actor_id=None,
    )
    evidence_service.upload_evidence(
        db,
        supplier_service.ENTITY_TYPE,
        models.id,
        None,
        _fake_upload("northwind-msa.pdf", b"Demo master services agreement."),
        "Master services agreement",
        actor_id=None,
    )
    _tag(db, supplier_service.ENTITY_TYPE, models.id, "iso_42001:A.10.2", "iso_42001:A.10.3")

    cloud = supplier_service.create_supplier(
        db,
        SupplierCreate(
            name="Contoso Cloud",
            supplier_type="infrastructure",
            description="Hosting and GPU compute for production models.",
            owner_id=PLACEHOLDER_USER_ID,
            contract_reference="CC-ENT-7731",
            contract_start=today - timedelta(days=300),
            contract_end=today + timedelta(days=430),
            review_interval_months=12,
            first_review_due=today - timedelta(days=10),
        ),
        actor_id=None,
    )
    supplier_service.set_ai_systems(db, cloud.id, [fraud_row_id, chatbot_row_id], actor_id=None)
    for row_id in (fraud_row_id, chatbot_row_id):
        supplier_service.update_link(
            db,
            cloud.id,
            row_id,
            SupplierAISystemLinkUpdate(supplier_role="component_supplier"),
            actor_id=None,
        )
    _tag(db, supplier_service.ENTITY_TYPE, cloud.id, "iso_42001:A.10.2")

    labelling = supplier_service.create_supplier(
        db,
        SupplierCreate(
            name="DataVista Labelling",
            supplier_type="data_provider",
            description="Labelled historical transactions used to train the fraud model.",
            contract_end=today - timedelta(days=60),
        ),
        actor_id=None,
    )
    supplier_service.update_supplier(
        db, labelling.id, SupplierUpdate(status="inactive"), actor_id=None
    )


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
