"""What an employee can see -- the one thing an employee login reaches.

Employees use AI systems but not this platform, so the portal shows them
the minimum: the policies and procedures the organization has chosen to
share with them, and (with the concerns feature) a way to raise a concern.
Everything here is built from an allowlist -- approved *and* shared records,
and only the fields an employee needs -- rather than from the internal
records minus what's hidden, so a field added to a policy later doesn't leak.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.evidence import Evidence
from app.models.policy import Policy, PolicyStatus
from app.models.procedure import Procedure, ProcedureStatus
from app.repositories import evidence_repository
from app.schemas.staff import StaffDocument, StaffLibraryItem

POLICY_ENTITY_TYPE = "Policy"
PROCEDURE_ENTITY_TYPE = "Procedure"


def _documents(db: Session, entity_type: str, entity_id: int) -> list[StaffDocument]:
    return [
        StaffDocument(
            id=evidence.id,
            filename=evidence.filename,
            content_type=evidence.content_type,
            size_bytes=evidence.size_bytes,
        )
        for evidence in evidence_repository.list_for_entity(db, entity_type, entity_id)
    ]


def _shared_policies(db: Session) -> list[Policy]:
    return list(
        db.scalars(
            select(Policy)
            .where(Policy.shared_with_employees.is_(True), Policy.status == PolicyStatus.APPROVED)
            .order_by(Policy.title, Policy.id)
        )
    )


def _shared_procedures(db: Session) -> list[Procedure]:
    return list(
        db.scalars(
            select(Procedure)
            .where(
                Procedure.shared_with_employees.is_(True),
                Procedure.status == ProcedureStatus.APPROVED,
            )
            .order_by(Procedure.title, Procedure.id)
        )
    )


def library(db: Session) -> list[StaffLibraryItem]:
    """The approved policies and procedures shared with employees. Anything in
    draft, in review or retired is never listed, however it's flagged."""
    items = [
        StaffLibraryItem(
            kind="policy",
            id=policy.id,
            title=policy.title,
            description=policy.description,
            version=policy.version,
            effective_date=policy.effective_date,
            documents=_documents(db, POLICY_ENTITY_TYPE, policy.id),
        )
        for policy in _shared_policies(db)
    ]
    items += [
        StaffLibraryItem(
            kind="procedure",
            id=procedure.id,
            title=procedure.title,
            description=procedure.description,
            version=procedure.version,
            effective_date=procedure.effective_date,
            documents=_documents(db, PROCEDURE_ENTITY_TYPE, procedure.id),
        )
        for procedure in _shared_procedures(db)
    ]
    return items


def shared_document(db: Session, evidence_id: int) -> Evidence:
    """A document an employee may download: one attached to an approved policy
    or procedure that is shared with them. Anything else is "not found" -- the
    same answer whether the file doesn't exist or just isn't theirs, so its
    existence doesn't leak."""
    evidence = db.get(Evidence, evidence_id)
    if evidence is not None:
        if evidence.entity_type == POLICY_ENTITY_TYPE and any(
            policy.id == evidence.entity_id for policy in _shared_policies(db)
        ):
            return evidence
        if evidence.entity_type == PROCEDURE_ENTITY_TYPE and any(
            procedure.id == evidence.entity_id for procedure in _shared_procedures(db)
        ):
            return evidence
    raise NotFoundError("Document", evidence_id)
