from datetime import date
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.repositories import (
    competence_repository,
    internal_audit_repository,
    management_review_repository,
    policy_repository,
    procedure_repository,
    risk_assessment_repository,
    supplier_repository,
)
from app.seed import PLACEHOLDER_USER_ID, seed
from app.services import (
    ai_incident_service,
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    ai_tool_service,
    change_service,
    communication_service,
    compliance_status_service,
    concern_service,
    corrective_action_service,
    improvement_service,
    internal_audit_service,
    management_review_service,
    objective_service,
    organization_context_service,
    risk_assessment_service,
    staff_service,
    supplier_service,
)


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
    assert total_risk_items == 4


def test_seed_creates_an_approved_policy_with_a_document(db_session: Session) -> None:
    seed(db_session)

    policies = policy_repository.list_all(db_session)
    approved = next(p for p in policies if p.title == "Data Retention Policy")

    assert approved.status == "approved"
    assert approved.version == 2  # bumped once by the seeded document upload


def test_seed_populates_internal_audits_and_management_review(db_session: Session) -> None:
    seed(db_session)

    programs = {p.title: p for p in internal_audit_repository.list_programs(db_session)}
    annual = programs["Annual AI Management System Audit"]
    annual_audits = internal_audit_repository.list_for_program(db_session, annual.id)
    assert [a.status for a in annual_audits] == ["completed"]
    assert internal_audit_service.is_overdue(annual, annual_audits) is False
    findings = internal_audit_repository.list_for_audit(db_session, annual_audits[0].id)
    nonconformity = next(f for f in findings if f.finding_type == "nonconformity")
    assert corrective_action_service.list_for_source(db_session, "AuditFinding", nonconformity.id)

    settings = management_review_repository.get_settings(db_session)
    meetings = management_review_repository.list_meetings(db_session)
    assert len(meetings) == 1
    assert management_review_service.is_overdue(settings, meetings) is False


def test_seed_populates_incidents_with_a_linked_corrective_action(db_session: Session) -> None:
    seed(db_session)

    incidents = {i.title: i for i in ai_incident_service.list_incidents(db_session)}
    assert len(incidents) == 3
    serious = incidents["Legitimate transactions blocked in one region"]
    assert serious.is_serious and serious.status == "resolved"
    assert ai_incident_service.is_reporting_overdue(serious) is False
    open_incident = incidents["Chatbot gave medication dosage advice"]
    assert corrective_action_service.list_for_source(db_session, "AIIncident", open_incident.id)


def test_seed_risk_owners_are_user_ids(db_session: Session) -> None:
    # The Risk Owner column is a user select keyed by stringified user id;
    # free text like "ML Team" shows up as "(unrecognized)" in the grid.
    seed(db_session)

    owners = {
        row.data["risk_owner"]
        for ra in risk_assessment_repository.list_all(db_session)
        for row in risk_assessment_service.list_rows(db_session, ra.id)
    }
    assert owners == {str(PLACEHOLDER_USER_ID)}


def test_seed_populates_competence_and_suppliers(db_session: Session) -> None:
    seed(db_session)

    requirements = competence_repository.list_requirements(db_session)
    assert len(requirements) == 3
    assert {r.governance_role_id is None for r in requirements} == {True, False}

    suppliers = {s.name: s for s in supplier_repository.list_all(db_session)}
    review_dates = supplier_service.review_dates_by_supplier(db_session)

    def standing(name: str):
        return supplier_service.standing(suppliers[name], review_dates[suppliers[name].id])

    assert standing("Northwind Model Labs").contract_status == "expiring"
    assert standing("Northwind Model Labs").review_overdue is False
    assert standing("Contoso Cloud").review_overdue is True
    assert standing("DataVista Labelling") == supplier_service.Standing(None, False, None)
    assert (
        len(supplier_service.linked_ai_system_ids(db_session, suppliers["Contoso Cloud"].id)) == 2
    )


def test_seed_populates_objectives_on_and_off_track(db_session: Session) -> None:
    seed(db_session)

    meeting = management_review_service.list_meetings(db_session)[0]
    now = {o.title: s.state for o, s in objective_service.standings_as_of(db_session, date.today())}
    then = {
        o.title: s.state
        for o, s in objective_service.standings_as_of(db_session, meeting.meeting_date)
    }

    assert now == {
        "Resume Screener passes its bias test suite": "on_track",
        "Every AI vendor is assessed before procurement": "off_track",
        "Publish an AI transparency notice for the support chatbot": "in_progress",
    }
    # At last month's management review the bias objective was still short.
    assert then["Resume Screener passes its bias test suite"] == "off_track"
    counts = objective_service.attention_counts(db_session, date.today())
    assert (counts.falling_short, counts.measurement_overdue) == (1, 0)


def test_seed_approves_the_context_and_tags_its_clauses(db_session: Session) -> None:
    seed(db_session)

    context = organization_context_service.get_or_create(db_session)
    rows = {
        row.code: row.status
        for row in compliance_status_service.get_status(db_session, "iso_42001")
        if row.code in ("4.1", "4.2", "4.3")
    }

    assert context.status == "approved"
    assert context.aims_scope and context.aims_scope_exclusions
    assert rows == {"4.1": "satisfied", "4.2": "satisfied", "4.3": "satisfied"}


def test_seed_records_the_organizations_ai_roles_and_the_chatbots_own(
    db_session: Session,
) -> None:
    seed(db_session)

    rows = {row.data["name"]: row for row in ai_system_inventory_service.list_rows(db_session)}
    chatbot = ai_system_lifecycle_service.get_or_create(
        db_session, rows["Customer Support Chatbot"].id
    )
    screener = ai_system_lifecycle_service.get_or_create(db_session, rows["Resume Screener"].id)

    assert organization_context_service.current_ai_roles(db_session) == [
        "developer",
        "integrator",
        "ai_user",
    ]
    assert ai_system_lifecycle_service.effective_ai_roles(db_session, chatbot) == ["ai_user"]
    assert ai_system_lifecycle_service.effective_ai_roles(db_session, screener) == [
        "developer",
        "integrator",
        "ai_user",
    ]


def test_seed_populates_changes_as_they_stood_at_the_management_review(
    db_session: Session,
) -> None:
    seed(db_session)

    meeting = management_review_service.list_meetings(db_session)[0]
    now = {
        c.title: (s.state, s.overdue)
        for c, s in change_service.standings_as_of(db_session, date.today())
    }
    then = {
        c.title: (s.state, s.overdue)
        for c, s in change_service.standings_as_of(db_session, meeting.meeting_date)
    }

    assert now == {
        "Introduce a fairness gate in the release pipeline": ("implemented", False),
        "Move the Resume Screener to a new base model": ("in_progress", False),
        "Replace the support chatbot vendor": ("planned", True),
        # Planned today, from an accepted improvement.
        "Name risk owners as individuals, not teams": ("planned", False),
    }
    # At last month's review the fairness gate was under way, and not yet late.
    assert then["Introduce a fairness gate in the release pipeline"] == ("in_progress", False)
    assert change_service.overdue_count(db_session) == 1


def test_seed_populates_a_communication_plan_with_one_lapsed_item(db_session: Session) -> None:
    seed(db_session)

    dates = communication_service.dates_by_item(db_session)
    standings = {
        item.topic: communication_service.standing(item, dates[item.id])
        for item in communication_service.list_items(db_session)
    }

    assert standings["Quarterly AI governance update"].overdue is False
    assert standings["Annual AI transparency notice"].overdue is True
    event_driven = standings["Notification of a serious AI incident"]
    assert (event_driven.next_due, event_driven.overdue) == (None, False)
    assert communication_service.overdue_count(db_session) == 1


def test_seed_tags_ai_systems_to_the_resource_controls(db_session: Session) -> None:
    seed(db_session)

    status = {
        row.code: row
        for row in compliance_status_service.get_status(db_session, "iso_42001")
        if row.code.startswith("A.4.")
    }

    for code in ("A.4.2", "A.4.3", "A.4.4", "A.4.6"):
        assert status[code].status == "satisfied", code
    # The Fraud Detection Model has no compute or hosting recorded.
    assert status["A.4.5"].status == "partial"
    missing = [i.detail for i in status["A.4.5"].tagged_items if not i.current]
    assert missing == ["Not recorded yet: Compute Infrastructure, Hosting Environment"]


def test_seed_tags_ai_systems_to_logging_and_information_controls(
    db_session: Session,
) -> None:
    seed(db_session)

    status = {
        row.code: row
        for row in compliance_status_service.get_status(db_session, "iso_42001")
        if row.code in ("A.6.2.8", "A.8.2", "A.10.4")
    }

    assert status["A.8.2"].status == "satisfied"
    assert status["A.10.4"].status == "satisfied"
    # The chatbot's logging isn't recorded; the Resume Screener's is.
    assert status["A.6.2.8"].status == "partial"
    missing = [(i.label, i.detail) for i in status["A.6.2.8"].tagged_items if not i.current]
    assert missing == [
        ("Customer Support Chatbot", "Not recorded yet: Event Logging, Log Retention")
    ]


def test_seed_shares_the_approved_retention_policy_with_employees(db_session: Session) -> None:
    seed(db_session)

    library = staff_service.library(db_session)

    assert [(item.kind, item.title) for item in library] == [("policy", "Data Retention Policy")]
    assert [d.filename for d in library[0].documents] == ["data-retention-policy-v1.pdf"]


def test_seed_populates_concerns_one_of_which_is_overdue_for_acknowledgement(
    db_session: Session,
) -> None:
    seed(db_session)

    concerns = {c.channel + "/" + c.status: c for c in concern_service.list_concerns(db_session)}
    standing = concern_service.standing(db_session)

    assert set(concerns) == {
        "employee_portal/under_review",
        "employee_portal/resolved",
        "phone/received",
    }
    assert concerns["employee_portal/resolved"].is_anonymous is True
    assert concerns["employee_portal/resolved"].reporter_id is None
    assert (standing.open_count, standing.awaiting_triage_count) == (2, 1)
    # The demo tracking code finds the anonymous concern.
    found = concern_service.lookup(db_session, SimpleNamespace(id=999), "kmnp 2345 hjkw")
    assert found.id == concerns["employee_portal/resolved"].id


def test_seed_is_idempotent(db_session: Session) -> None:
    seed(db_session)
    seed(db_session)

    policies = policy_repository.list_all(db_session)

    assert len(policies) == 2


def test_seed_populates_the_improvement_register(db_session: Session) -> None:
    seed(db_session)

    standings = {
        improvement.title: (standing.state, standing.overdue)
        for improvement, standing in improvement_service.standings_as_of(db_session, date.today())
    }
    assert standings == {
        "Name risk owners as individuals, not teams": ("accepted", False),
        "Tell customers when they are talking to an AI, in every product": (
            "implemented",
            False,
        ),
        "Publish a model card for every internal AI tool": ("accepted", True),
    }
    status = next(
        row
        for row in compliance_status_service.get_status(db_session, "iso_42001")
        if row.code == "10.1"
    )
    assert status.status == "partial"
    assert [i.label for i in status.tagged_items if not i.current] == [
        "Publish a model card for every internal AI tool"
    ]


def test_the_script_entry_point_comes_after_everything_it_calls() -> None:
    # `python -m app.seed` runs main() as soon as the guard is reached, so a
    # helper defined below it doesn't exist yet when seed() calls it -- the
    # tests, importing the whole module first, wouldn't notice.
    import ast
    import inspect

    import app.seed as seed_module

    tree = ast.parse(inspect.getsource(seed_module))
    guard = tree.body[-1]
    assert isinstance(guard, ast.If)
    assert ast.unparse(guard.test) == "__name__ == '__main__'"


def test_seed_populates_the_ai_tool_register(db_session: Session) -> None:
    seed(db_session)

    tools = {t.name: t for t in ai_tool_service.list_tools(db_session)}
    assert {n: t.status for n, t in tools.items() if t.status != "catalogued"} == {
        "Microsoft Copilot": "approved",
        "Perplexity": "restricted",
        "ChatGPT": "approved",
    }
    assert len(tools) == 12
    assert ai_tool_service.review_overdue(tools["ChatGPT"])
    assert not ai_tool_service.review_overdue(tools["Microsoft Copilot"])
    assert ai_tool_service.pending_request_count(db_session) == 1
    statuses = {r.tool_name: r.status for r in ai_tool_service.list_requests(db_session)}
    assert statuses == {"Claude": "requested", "Character.AI": "rejected"}
    status = next(
        row
        for row in compliance_status_service.get_status(db_session, "iso_42001")
        if row.code == "A.9.2"
    )
    assert status.status == "partial"
    assert [i.label for i in status.tagged_items if not i.current] == ["ChatGPT"]
