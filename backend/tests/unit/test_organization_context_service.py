"""ISO/IEC 42001 Clause 4: context of the organization.

One record for the whole deployment, with a single-stage CAIGO-gated
approval like Policy -- but unlike a Policy, editing it after approval
withdraws the approval and returns it to draft rather than refusing the
edit, the same rule risk_assessment_service.add_row/update_row applies to
a risk item.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStatusTransitionError, ValidationError
from app.models.audit_log import AuditLogEntry
from app.models.organization_context import OrganizationContextStatus
from app.services import organization_context_service as service


def approved(db: Session):
    service.get_or_create(db)
    service.update(
        db,
        {
            "organization_description": "We build things.",
            "ai_usage_overview": "We use AI to help draft records.",
        },
        actor_id=None,
    )
    service.submit_for_review(db, actor_id=None)
    return service.approve(db, actor_id=None)


# ---------- the singleton record and its two sheets ----------


def test_get_or_create_provisions_both_sheets_once(db_session: Session) -> None:
    context = service.get_or_create(db_session)

    again = service.get_or_create(db_session)

    assert again.id == context.id
    assert again.issues_sheet_id == context.issues_sheet_id
    assert again.interested_parties_sheet_id == context.interested_parties_sheet_id
    assert context.status == OrganizationContextStatus.DRAFT


def test_the_two_sheets_start_with_their_default_columns(db_session: Session) -> None:
    from app.services import sheet_service

    context = service.get_or_create(db_session)

    issues_sheet = sheet_service.get_sheet(db_session, context.issues_sheet_id)
    parties_sheet = sheet_service.get_sheet(db_session, context.interested_parties_sheet_id)

    assert [c["key"] for c in issues_sheet.columns] == ["category", "issue", "planned_response"]
    assert [c["key"] for c in parties_sheet.columns] == [
        "party",
        "needs",
        "expectations",
        "requirements",
    ]


# ---------- narrative ----------


def test_update_sets_both_narrative_fields(db_session: Session) -> None:
    service.get_or_create(db_session)

    context = service.update(
        db_session,
        {
            "organization_description": "A resume-screening company.",
            "ai_usage_overview": "Ranks applicants.",
        },
        actor_id=None,
    )

    assert context.organization_description == "A resume-screening company."
    assert context.ai_usage_overview == "Ranks applicants."


def test_updating_one_field_does_not_blank_the_other(db_session: Session) -> None:
    """A save of one narrative field is a partial update, not a full
    overwrite -- the other field, mid-edit or already saved, must survive."""
    service.get_or_create(db_session)
    service.update(db_session, {"ai_usage_overview": "Ranks applicants."}, actor_id=None)

    context = service.update(
        db_session, {"organization_description": "A resume-screening company."}, actor_id=None
    )

    assert context.organization_description == "A resume-screening company."
    assert context.ai_usage_overview == "Ranks applicants."


def test_update_is_audit_logged(db_session: Session) -> None:
    service.get_or_create(db_session)

    service.update(db_session, {"organization_description": "Org."}, actor_id=None)

    entry = db_session.query(AuditLogEntry).filter(AuditLogEntry.action == "updated").one()
    assert entry.entity_type == "OrganizationContext"


# ---------- approval ----------


def test_submit_for_review_transitions_draft_to_in_review(db_session: Session) -> None:
    service.get_or_create(db_session)

    result = service.submit_for_review(db_session, actor_id=None)

    assert result.status == OrganizationContextStatus.IN_REVIEW


def test_submit_for_review_rejects_non_draft(db_session: Session) -> None:
    service.get_or_create(db_session)
    service.submit_for_review(db_session, actor_id=None)

    with pytest.raises(InvalidStatusTransitionError):
        service.submit_for_review(db_session, actor_id=None)


def test_approve_transitions_in_review_to_approved_and_schedules_a_review(
    db_session: Session,
) -> None:
    service.get_or_create(db_session)
    service.submit_for_review(db_session, actor_id=None)

    result = service.approve(db_session, actor_id=None)

    assert result.status == OrganizationContextStatus.APPROVED
    assert result.next_review_date is not None


def test_approve_rejects_non_in_review(db_session: Session) -> None:
    service.get_or_create(db_session)

    with pytest.raises(InvalidStatusTransitionError):
        service.approve(db_session, actor_id=None)


# ---------- editing an approved record withdraws it ----------


def test_editing_the_narrative_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    context = service.update(
        db_session, {"organization_description": "Changed description."}, actor_id=None
    )

    assert context.status == OrganizationContextStatus.DRAFT
    assert context.approved_by is None
    assert context.approved_at is None


def test_an_unrelated_update_that_changes_nothing_does_not_withdraw(db_session: Session) -> None:
    context = approved(db_session)

    result = service.update(
        db_session,
        {
            "organization_description": context.organization_description,
            "ai_usage_overview": context.ai_usage_overview,
        },
        actor_id=None,
    )

    assert result.status == OrganizationContextStatus.APPROVED


def test_adding_an_issue_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    service.add_issue(
        db_session, {"category": "Internal", "issue": "Staff turnover"}, actor_id=None
    )

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_updating_an_issue_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)
    row = service.add_issue(db_session, {"category": "Internal", "issue": "x"}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    service.update_issue(db_session, row.id, {"issue": "Revised."}, actor_id=None)

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_deleting_an_issue_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)
    row = service.add_issue(db_session, {"category": "Internal", "issue": "x"}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    service.delete_issue(db_session, row.id, actor_id=None)

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_adding_an_interested_party_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    service.add_interested_party(
        db_session, {"party": "Regulators", "needs": "Compliance evidence"}, actor_id=None
    )

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_updating_an_interested_party_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)
    row = service.add_interested_party(db_session, {"party": "Regulators"}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    service.update_interested_party(db_session, row.id, {"needs": "Revised."}, actor_id=None)

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_deleting_an_interested_party_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)
    row = service.add_interested_party(db_session, {"party": "Regulators"}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    service.delete_interested_party(db_session, row.id, actor_id=None)

    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_two_people_approving_at_once_cannot_both_succeed(db_session: Session) -> None:
    """The race the status check can't catch: both requests read the record
    as in_review before either writes. Only the conditional claim decides
    which wins -- see risk_item_suggestion_service's identical race test."""
    from unittest.mock import patch

    from sqlalchemy import update as sa_update

    from app.models.organization_context import OrganizationContext

    context = service.get_or_create(db_session)
    service.submit_for_review(db_session, actor_id=None)
    stale = service.get_or_create(db_session)  # a second reader's own copy, still in_review

    # The other request wins between this one's read and its write: the row is
    # approved in the database, while the stale copy still says in_review.
    db_session.execute(
        sa_update(OrganizationContext)
        .where(OrganizationContext.id == context.id)
        .values(status=OrganizationContextStatus.APPROVED)
        .execution_options(synchronize_session=False)
    )
    assert stale.status == OrganizationContextStatus.IN_REVIEW  # the stale read the race produces

    with patch.object(service, "get_or_create", return_value=stale):
        with pytest.raises(InvalidStatusTransitionError):
            service.approve(db_session, actor_id=None)


# ---------- bulk upload and export ----------


def _upload(content: bytes, filename: str = "issues.csv"):
    import io
    from types import SimpleNamespace

    return SimpleNamespace(filename=filename, file=io.BytesIO(content))


def test_importing_issues_creates_rows_and_withdraws_approval(db_session: Session) -> None:
    approved(db_session)
    csv_content = b"Category,Issue\nInternal,Staff turnover\n"

    service.import_issues_upload(db_session, _upload(csv_content), actor_id=None)

    rows = service.list_issues(db_session)
    assert rows[0].data == {"category": "Internal", "issue": "Staff turnover"}
    context = service.get_or_create(db_session)
    assert context.status == OrganizationContextStatus.DRAFT


def test_importing_interested_parties_creates_rows(db_session: Session) -> None:
    csv_content = b"Party,Needs\nRegulators,Compliance evidence\n"

    service.import_interested_parties_upload(
        db_session, _upload(csv_content, "parties.csv"), actor_id=None
    )

    rows = service.list_interested_parties(db_session)
    assert rows[0].data == {"party": "Regulators", "needs": "Compliance evidence"}


def test_exporting_issues_returns_xlsx_bytes(db_session: Session) -> None:
    service.add_issue(db_session, {"category": "Internal", "issue": "x"}, actor_id=None)

    content = service.export_issues_xlsx(db_session)

    assert content[:2] == b"PK"  # xlsx is a zip archive


def test_exporting_interested_parties_returns_xlsx_bytes(db_session: Session) -> None:
    service.add_interested_party(db_session, {"party": "Regulators"}, actor_id=None)

    content = service.export_interested_parties_xlsx(db_session)

    assert content[:2] == b"PK"


# ---------- the organization's AI roles (ISO/IEC 22989) ----------


def test_ai_roles_start_empty_and_can_be_saved(db_session: Session) -> None:
    assert service.get_or_create(db_session).ai_roles == []

    context = service.update(db_session, {"ai_roles": ["developer", "ai_user"]}, actor_id=None)

    assert context.ai_roles == ["developer", "ai_user"]
    assert service.current_ai_roles(db_session) == ["developer", "ai_user"]


def test_ai_roles_are_kept_in_the_standards_order_without_duplicates(
    db_session: Session,
) -> None:
    context = service.update(
        db_session, {"ai_roles": ["ai_user", "developer", "ai_user"]}, actor_id=None
    )

    assert context.ai_roles == ["developer", "ai_user"]


def test_an_unknown_ai_role_is_refused_and_nothing_is_saved(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        service.update(db_session, {"ai_roles": ["developer", "wizard"]}, actor_id=None)

    assert service.current_ai_roles(db_session) == []


def test_saving_one_field_leaves_the_ai_roles_alone(db_session: Session) -> None:
    service.update(db_session, {"ai_roles": ["developer"]}, actor_id=None)

    service.update(db_session, {"organization_description": "We build things."}, actor_id=None)

    assert service.current_ai_roles(db_session) == ["developer"]


def test_changing_the_ai_roles_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    context = service.update(db_session, {"ai_roles": ["developer"]}, actor_id=None)

    assert context.status == OrganizationContextStatus.DRAFT


def test_resaving_the_same_ai_roles_does_not_withdraw_approval(db_session: Session) -> None:
    service.update(db_session, {"ai_roles": ["developer", "ai_user"]}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    # The same set picked in a different order.
    context = service.update(db_session, {"ai_roles": ["ai_user", "developer"]}, actor_id=None)

    assert context.status == OrganizationContextStatus.APPROVED


def test_reading_the_ai_roles_does_not_provision_the_context(db_session: Session) -> None:
    assert service.current_ai_roles(db_session) == []

    from app.models.organization_context import OrganizationContext

    assert db_session.query(OrganizationContext).count() == 0


# ---------- the scope of the AI management system (4.3) ----------


def test_the_scope_starts_empty_and_is_saved_with_its_exclusions(db_session: Session) -> None:
    context = service.get_or_create(db_session)
    assert (context.aims_scope, context.aims_scope_exclusions) == (None, None)

    context = service.update(
        db_session,
        {
            "aims_scope": "All AI systems built or bought by the Berlin and Lisbon offices.",
            "aims_scope_exclusions": "Research prototypes that never touch production data.",
        },
        actor_id=None,
    )

    assert context.aims_scope.startswith("All AI systems")
    assert context.aims_scope_exclusions.startswith("Research prototypes")


def test_saving_the_scope_leaves_the_other_fields_alone(db_session: Session) -> None:
    service.update(
        db_session,
        {"organization_description": "We build things.", "ai_roles": ["developer"]},
        actor_id=None,
    )

    service.update(db_session, {"aims_scope": "Everything."}, actor_id=None)

    context = service.get_or_create(db_session)
    assert context.organization_description == "We build things."
    assert context.ai_roles == ["developer"]
    assert context.aims_scope_exclusions is None


def test_changing_the_scope_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    context = service.update(db_session, {"aims_scope": "Everything."}, actor_id=None)

    assert context.status == OrganizationContextStatus.DRAFT


def test_changing_only_the_exclusions_after_approval_withdraws_it(db_session: Session) -> None:
    approved(db_session)

    context = service.update(db_session, {"aims_scope_exclusions": "Prototypes."}, actor_id=None)

    assert context.status == OrganizationContextStatus.DRAFT


def test_resaving_the_same_exclusions_does_not_withdraw_approval(db_session: Session) -> None:
    service.update(db_session, {"aims_scope_exclusions": "Prototypes."}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    context = service.update(db_session, {"aims_scope_exclusions": "Prototypes."}, actor_id=None)

    assert context.status == OrganizationContextStatus.APPROVED


def test_resaving_the_same_scope_does_not_withdraw_approval(db_session: Session) -> None:
    service.update(db_session, {"aims_scope": "Everything."}, actor_id=None)
    service.submit_for_review(db_session, actor_id=None)
    service.approve(db_session, actor_id=None)

    context = service.update(db_session, {"aims_scope": "Everything."}, actor_id=None)

    assert context.status == OrganizationContextStatus.APPROVED
