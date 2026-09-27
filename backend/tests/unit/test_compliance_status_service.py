"""Compliance status: computed live from tags, the Statement of
Applicability, and the state of whatever a control is tagged to -- never a
manual status someone sets by hand."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories import framework_control_repository
from app.schemas.corrective_action import CorrectiveActionCreate
from app.schemas.internal_audit import AuditProgramCreate
from app.schemas.policy import PolicyCreate
from app.services import (
    compliance_status_service,
    corrective_action_service,
    framework_service,
    internal_audit_service,
    policy_service,
)


def clause_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001", "clause")[0].id


def annex_a_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001", "annex_a_control")[0].id


def eu_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "eu_ai_act")[0].id


def make_policy(db: Session, **overrides) -> int:
    policy = policy_service.create_policy(
        db, PolicyCreate(title="Data Retention Policy", description="x"), actor_id=None
    )
    return policy.id


def status_for(db: Session, control_id: int):
    return next(row for row in compliance_status_service.get_status(db) if row.id == control_id)


# ---------- no coverage ----------


def test_an_untagged_control_has_no_coverage(db_session: Session) -> None:
    control_id = clause_control_id(db_session)

    row = status_for(db_session, control_id)

    assert row.status == "no_coverage"
    assert row.tagged_items == []


def test_a_tag_whose_record_was_deleted_reads_as_no_coverage(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    policy_id = make_policy(db_session)
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)
    policy_service.delete_policy(db_session, policy_id, actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "no_coverage"


# ---------- partial: draft, retired, or stale ----------


def test_a_control_tagged_to_a_draft_policy_is_partial(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    policy_id = make_policy(db_session)
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert row.tagged_items[0].current is False
    assert "draft" in row.tagged_items[0].detail.lower()


def test_a_control_tagged_to_a_retired_policy_is_partial(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    policy_id = make_policy(db_session)
    policy_service.submit_for_review(db_session, policy_id, actor_id=None)
    policy_service.approve_policy(db_session, policy_id, actor_id=None)
    policy_service.retire_policy(db_session, policy_id, actor_id=None)
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert "retired" in row.tagged_items[0].detail.lower()


def test_an_approved_policy_whose_review_date_has_passed_is_partial(db_session: Session) -> None:
    from app.models.policy import Policy

    control_id = clause_control_id(db_session)
    policy_id = make_policy(db_session)
    policy_service.submit_for_review(db_session, policy_id, actor_id=None)
    policy_service.approve_policy(db_session, policy_id, actor_id=None)
    record = db_session.get(Policy, policy_id)
    record.next_review_date = date.today() - timedelta(days=1)
    db_session.commit()
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert row.tagged_items[0].current is False
    assert "review date" in row.tagged_items[0].detail.lower()


# ---------- satisfied ----------


def test_a_control_tagged_only_to_an_approved_current_policy_is_satisfied(
    db_session: Session,
) -> None:
    control_id = clause_control_id(db_session)
    policy_id = make_policy(db_session)
    policy_service.submit_for_review(db_session, policy_id, actor_id=None)
    policy_service.approve_policy(db_session, policy_id, actor_id=None)
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "satisfied"
    assert row.tagged_items[0].current is True


def test_one_stale_item_among_several_makes_the_whole_control_partial(
    db_session: Session,
) -> None:
    control_id = clause_control_id(db_session)
    approved_id = make_policy(db_session)
    policy_service.submit_for_review(db_session, approved_id, actor_id=None)
    policy_service.approve_policy(db_session, approved_id, actor_id=None)
    draft_id = make_policy(db_session)
    framework_service.set_tags(
        db_session, "Policy", approved_id, [control_id], actor_id=None
    )
    framework_service.set_tags(db_session, "Policy", draft_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert {item.current for item in row.tagged_items} == {True, False}


def test_evidence_counts_as_satisfied_once_attached(db_session: Session) -> None:
    from app.models.evidence import Evidence

    control_id = clause_control_id(db_session)
    evidence = Evidence(
        entity_type="Policy",
        entity_id=1,
        folder_id=None,
        filename="signed.pdf",
        content_type="application/pdf",
        size_bytes=10,
        storage_path="/tmp/signed.pdf",
    )
    db_session.add(evidence)
    db_session.commit()
    framework_service.set_tags(db_session, "Evidence", evidence.id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "satisfied"
    assert row.tagged_items[0].label == "signed.pdf"


# ---------- not applicable ----------


def test_an_annex_a_control_marked_not_applicable_is_not_applicable_even_if_tagged(
    db_session: Session,
) -> None:
    control_id = annex_a_control_id(db_session)
    policy_id = make_policy(db_session)
    framework_service.set_tags(db_session, "Policy", policy_id, [control_id], actor_id=None)
    framework_service.update_soa_entry(
        db_session, control_id, "not_applicable", "We don't operate this kind of system.",
        actor_id=None,
    )

    row = status_for(db_session, control_id)

    assert row.status == "not_applicable"
    assert row.reason == "We don't operate this kind of system."


def test_a_clause_or_eu_ai_act_control_ignores_soa_entirely(db_session: Session) -> None:
    """SoA is an Annex A mechanism only -- a main-body clause or an EU AI Act
    article was never given an SoA entry and must never read as excluded."""
    clause_id = clause_control_id(db_session)
    eu_id = eu_control_id(db_session)

    assert status_for(db_session, clause_id).status == "no_coverage"
    assert status_for(db_session, eu_id).status == "no_coverage"


# ---------- summary ----------


def test_summary_splits_counts_by_clause_annex_a_and_eu_ai_act(db_session: Session) -> None:
    summary = compliance_status_service.get_summary(db_session)

    all_clauses = framework_control_repository.list_all(db_session, "iso_42001", "clause")
    all_annex_a = framework_control_repository.list_all(db_session, "iso_42001", "annex_a_control")
    all_eu = framework_control_repository.list_all(db_session, "eu_ai_act")

    assert summary.iso_42001_clauses.no_coverage == len(all_clauses)
    assert summary.iso_42001_annex_a.no_coverage == len(all_annex_a)
    assert summary.eu_ai_act.no_coverage == len(all_eu)


def test_marking_one_annex_a_control_not_applicable_moves_it_out_of_no_coverage(
    db_session: Session,
) -> None:
    control_id = annex_a_control_id(db_session)
    before = compliance_status_service.get_summary(db_session).iso_42001_annex_a

    framework_service.update_soa_entry(
        db_session, control_id, "not_applicable", "Not in scope.", actor_id=None
    )
    after = compliance_status_service.get_summary(db_session).iso_42001_annex_a

    assert after.not_applicable == before.not_applicable + 1
    assert after.no_coverage == before.no_coverage - 1


# ---------- framework filter ----------


def test_get_status_can_be_filtered_by_framework(db_session: Session) -> None:
    rows = compliance_status_service.get_status(db_session, framework="eu_ai_act")

    assert len(rows) > 0
    assert all(row.framework == "eu_ai_act" for row in rows)


# ---------- corrective action ----------


def make_corrective_action(db: Session, **overrides) -> int:
    defaults = dict(
        title="Fix drift",
        nonconformity_description="x",
        assignee_id=1,
        due_date=date.today() + timedelta(days=14),
    )
    defaults.update(overrides)
    corrective_action = corrective_action_service.create_corrective_action(
        db, CorrectiveActionCreate(**defaults), actor_id=None
    )
    return corrective_action.id


def test_an_open_corrective_action_not_yet_due_is_current(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    ca_id = make_corrective_action(db_session)
    framework_service.set_tags(db_session, "CorrectiveAction", ca_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "satisfied"
    assert row.tagged_items[0].current is True


def test_an_overdue_open_corrective_action_is_partial(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    ca_id = make_corrective_action(db_session, due_date=date.today() - timedelta(days=1))
    framework_service.set_tags(db_session, "CorrectiveAction", ca_id, [control_id], actor_id=None)

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert row.tagged_items[0].current is False
    assert "overdue" in row.tagged_items[0].detail.lower()


# ---------- internal audit program ----------


def make_audit_program(db: Session, **overrides) -> int:
    defaults = dict(
        title="Annual AI System Audit",
        schedule_type="interval",
        interval_months=6,
        start_date=date.today() + timedelta(days=30),
    )
    defaults.update(overrides)
    program = internal_audit_service.create_audit_program(
        db, AuditProgramCreate(**defaults), actor_id=None
    )
    return program.id


def test_an_interval_program_not_yet_due_is_current(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    program_id = make_audit_program(db_session)
    framework_service.set_tags(
        db_session, "AuditProgram", program_id, [control_id], actor_id=None
    )

    row = status_for(db_session, control_id)

    assert row.status == "satisfied"
    assert row.tagged_items[0].current is True


def test_an_overdue_interval_program_is_partial(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    program_id = make_audit_program(
        db_session, start_date=date.today() - timedelta(days=1)
    )
    framework_service.set_tags(
        db_session, "AuditProgram", program_id, [control_id], actor_id=None
    )

    row = status_for(db_session, control_id)

    assert row.status == "partial"
    assert row.tagged_items[0].current is False
    assert "overdue" in row.tagged_items[0].detail.lower()


def test_an_ad_hoc_program_is_always_current(db_session: Session) -> None:
    control_id = clause_control_id(db_session)
    program_id = make_audit_program(
        db_session,
        schedule_type="ad_hoc",
        interval_months=None,
        start_date=date.today() - timedelta(days=3650),
    )
    framework_service.set_tags(
        db_session, "AuditProgram", program_id, [control_id], actor_id=None
    )

    row = status_for(db_session, control_id)

    assert row.status == "satisfied"
    assert row.tagged_items[0].current is True
