"""ISO/IEC 42001 Clause 4: context of the organization.

One record for the whole deployment -- there is no per-AI-system version of
this, the same shape as the AI System Inventory sheet or the AI Assist
settings row. Owns two organization-wide sheets (see app.models.sheet) for
its two tables: internal/external issues, and interested parties.

Approval is single-stage and CAIGO-gated, the same shape Policy uses. But
unlike a Policy -- a document superseded by a new version -- this record is
continuously maintained, so editing it after approval withdraws the
approval and returns it to draft, the same rule
risk_assessment_service.add_row/update_row applies to a risk item, rather
than Policy's "only editable while draft".
"""

from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ai_stakeholder_roles, review_cadence
from app.core.concurrency import claim_transition, withdraw_transition
from app.core.exceptions import InvalidStatusTransitionError, ValidationError
from app.models.organization_context import OrganizationContext, OrganizationContextStatus
from app.models.sheet import Sheet, SheetRow
from app.schemas.sheet import ColumnDef
from app.services import audit_service, governance_role_service, sheet_service

ENTITY_TYPE = "OrganizationContext"

ISSUES_ENTITY_TYPE = "OrganizationalIssues"
INTERESTED_PARTIES_ENTITY_TYPE = "InterestedParties"

ISSUES_COLUMNS = [
    ColumnDef(key="category", label="Category"),
    ColumnDef(key="issue", label="Issue"),
    ColumnDef(key="planned_response", label="Planned Response"),
]

INTERESTED_PARTIES_COLUMNS = [
    ColumnDef(key="party", label="Interested Party"),
    ColumnDef(key="needs", label="Needs"),
    ColumnDef(key="expectations", label="Expectations"),
    ColumnDef(key="requirements", label="Requirements"),
]


def validated_ai_roles(codes: list[str]) -> list[str]:
    """The codes de-duplicated, in the standard's order -- so the same set
    of roles is always the same list, and picking them in a different order
    isn't a change that withdraws the approval."""
    unknown = ai_stakeholder_roles.unknown_codes(codes)
    if unknown:
        raise ValidationError(f"Unknown AI role: {', '.join(unknown)}.")
    return [role.code for role in ai_stakeholder_roles.AI_ROLES if role.code in set(codes)]


def current_ai_roles(db: Session) -> list[str]:
    """The organization's AI roles, without provisioning the context record
    just to read them."""
    existing = db.scalar(select(OrganizationContext).order_by(OrganizationContext.id))
    return list(existing.ai_roles) if existing is not None else []


def get_or_create(db: Session) -> OrganizationContext:
    """The one context record, provisioned (with its two sheets) on first
    access. Not hardened against a simultaneous first-access race the way
    Sheet's own get_or_create_singleton_sheet is -- this record has no
    natural key to catch a duplicate insert on, and, like AiAssistSettings
    and RiskCriteria, it is an org-wide record an admin sets up once, not a
    hot path two requests plausibly race on."""
    existing = db.scalar(select(OrganizationContext).order_by(OrganizationContext.id))
    if existing is not None:
        return existing

    issues_sheet = sheet_service.get_or_create_singleton_sheet(
        db, ISSUES_ENTITY_TYPE, "Internal and External Issues", ISSUES_COLUMNS
    )
    parties_sheet = sheet_service.get_or_create_singleton_sheet(
        db, INTERESTED_PARTIES_ENTITY_TYPE, "Interested Parties", INTERESTED_PARTIES_COLUMNS
    )
    context = OrganizationContext(
        status=OrganizationContextStatus.DRAFT,
        issues_sheet_id=issues_sheet.id,
        interested_parties_sheet_id=parties_sheet.id,
    )
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


def _withdraw_approval(db: Session, context: OrganizationContext) -> None:
    if context.status == OrganizationContextStatus.DRAFT:
        return
    withdraw_transition(
        db,
        context,
        {
            "status": OrganizationContextStatus.DRAFT,
            "approved_by": None,
            "approved_at": None,
        },
    )


def update(db: Session, changes: dict, actor_id: int | None) -> OrganizationContext:
    """Only ``organization_description``, ``ai_usage_overview`` and/or
    ``ai_roles``, and only the ones actually given -- a save of one field
    must not blank out the others, the way it would if every save always
    wrote all of them."""
    context = get_or_create(db)
    if "ai_roles" in changes:
        changes = {**changes, "ai_roles": validated_ai_roles(changes["ai_roles"] or [])}
    before = {
        "organization_description": context.organization_description,
        "ai_usage_overview": context.ai_usage_overview,
        "ai_roles": context.ai_roles,
    }
    for field, value in changes.items():
        setattr(context, field, value)
    db.commit()
    audit_service.log(db, ENTITY_TYPE, context.id, "updated", actor_id, changes)
    if {**before, **changes} != before:
        _withdraw_approval(db, context)
    db.refresh(context)
    return context


def get_issues_sheet(db: Session) -> Sheet:
    context = get_or_create(db)
    return sheet_service.get_sheet(db, context.issues_sheet_id)


def get_interested_parties_sheet(db: Session) -> Sheet:
    context = get_or_create(db)
    return sheet_service.get_sheet(db, context.interested_parties_sheet_id)


def set_issues_columns(db: Session, columns: list[ColumnDef], actor_id: int | None) -> Sheet:
    context = get_or_create(db)
    result = sheet_service.set_columns(db, context.issues_sheet_id, columns)
    audit_service.log(db, ENTITY_TYPE, context.id, "issues_columns_updated", actor_id)
    _withdraw_approval(db, context)
    return result


def set_interested_parties_columns(
    db: Session, columns: list[ColumnDef], actor_id: int | None
) -> Sheet:
    context = get_or_create(db)
    result = sheet_service.set_columns(db, context.interested_parties_sheet_id, columns)
    audit_service.log(db, ENTITY_TYPE, context.id, "interested_parties_columns_updated", actor_id)
    _withdraw_approval(db, context)
    return result


def export_issues_xlsx(db: Session) -> bytes:
    context = get_or_create(db)
    return sheet_service.export_xlsx(db, context.issues_sheet_id)


def import_issues_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    context = get_or_create(db)
    # No natural_key_column: an issue has nothing as reliably unique as an AI
    # system's or a dataset's name, so only the file's own ID column (see
    # sheet_service.import_upload) can match a row back to itself.
    outcome = sheet_service.import_upload(db, context.issues_sheet_id, file)
    audit_service.log(db, ENTITY_TYPE, context.id, "issues_uploaded", actor_id)
    _withdraw_approval(db, context)
    return outcome.sheet


def export_interested_parties_xlsx(db: Session) -> bytes:
    context = get_or_create(db)
    return sheet_service.export_xlsx(db, context.interested_parties_sheet_id)


def import_interested_parties_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    context = get_or_create(db)
    outcome = sheet_service.import_upload(db, context.interested_parties_sheet_id, file)
    audit_service.log(db, ENTITY_TYPE, context.id, "interested_parties_uploaded", actor_id)
    _withdraw_approval(db, context)
    return outcome.sheet


def list_issues(db: Session) -> list[SheetRow]:
    context = get_or_create(db)
    return sheet_service.list_rows(db, context.issues_sheet_id)


def add_issue(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    context = get_or_create(db)
    row = sheet_service.add_row(db, context.issues_sheet_id, data)
    audit_service.log(db, ENTITY_TYPE, context.id, "issue_added", actor_id, {"row_id": row.id})
    _withdraw_approval(db, context)
    return row


def update_issue(db: Session, row_id: int, data: dict, actor_id: int | None) -> SheetRow:
    context = get_or_create(db)
    row = sheet_service.update_row(db, context.issues_sheet_id, row_id, data)
    audit_service.log(db, ENTITY_TYPE, context.id, "issue_updated", actor_id, {"row_id": row_id})
    _withdraw_approval(db, context)
    return row


def delete_issue(db: Session, row_id: int, actor_id: int | None) -> None:
    context = get_or_create(db)
    sheet_service.delete_row(db, context.issues_sheet_id, row_id)
    audit_service.log(db, ENTITY_TYPE, context.id, "issue_deleted", actor_id, {"row_id": row_id})
    _withdraw_approval(db, context)


def list_interested_parties(db: Session) -> list[SheetRow]:
    context = get_or_create(db)
    return sheet_service.list_rows(db, context.interested_parties_sheet_id)


def add_interested_party(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    context = get_or_create(db)
    row = sheet_service.add_row(db, context.interested_parties_sheet_id, data)
    audit_service.log(
        db, ENTITY_TYPE, context.id, "interested_party_added", actor_id, {"row_id": row.id}
    )
    _withdraw_approval(db, context)
    return row


def update_interested_party(db: Session, row_id: int, data: dict, actor_id: int | None) -> SheetRow:
    context = get_or_create(db)
    row = sheet_service.update_row(db, context.interested_parties_sheet_id, row_id, data)
    audit_service.log(
        db, ENTITY_TYPE, context.id, "interested_party_updated", actor_id, {"row_id": row_id}
    )
    _withdraw_approval(db, context)
    return row


def delete_interested_party(db: Session, row_id: int, actor_id: int | None) -> None:
    context = get_or_create(db)
    sheet_service.delete_row(db, context.interested_parties_sheet_id, row_id)
    audit_service.log(
        db, ENTITY_TYPE, context.id, "interested_party_deleted", actor_id, {"row_id": row_id}
    )
    _withdraw_approval(db, context)


def _claim(db: Session, context: OrganizationContext, expected: str, changes: dict) -> None:
    """Each status check above ran in a transaction of its own, so two
    simultaneous callers can both pass it. Re-stating the expected status in
    the write is what makes only one of them land."""
    if not claim_transition(db, context, expected_statuses=expected, changes=changes):
        raise InvalidStatusTransitionError(
            f"Context of the organization is no longer '{expected}' -- someone else "
            f"has already moved it on, and it is now '{context.status}'."
        )


def submit_for_review(db: Session, actor_id: int | None) -> OrganizationContext:
    context = get_or_create(db)
    if context.status != OrganizationContextStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Context of the organization must be in 'draft' status to submit for "
            f"review, currently '{context.status}'"
        )
    _claim(
        db,
        context,
        OrganizationContextStatus.DRAFT,
        {"status": OrganizationContextStatus.IN_REVIEW},
    )
    audit_service.log(db, ENTITY_TYPE, context.id, "submitted_for_review", actor_id)
    return context


def approve(db: Session, actor_id: int | None) -> OrganizationContext:
    context = get_or_create(db)
    if context.status != OrganizationContextStatus.IN_REVIEW:
        raise InvalidStatusTransitionError(
            f"Context of the organization must be in 'in_review' status to approve, "
            f"currently '{context.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(db, ENTITY_TYPE, context.id, actor_id)
    _claim(
        db,
        context,
        OrganizationContextStatus.IN_REVIEW,
        {
            "status": OrganizationContextStatus.APPROVED,
            "approved_by": actor_id,
            "approved_at": datetime.now(UTC),
            "next_review_date": review_cadence.next_review_date(datetime.now(UTC).date()),
        },
    )
    audit_service.log(db, ENTITY_TYPE, context.id, "approved", actor_id)
    return context
