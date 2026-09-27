"""Internal audit management -- ISO/IEC 42001 Clause 9.2.

Three entities, one file, mirroring impact_assessment_service.py covering
ImpactAssessment and ImpactFactorAssessment together:

- AuditProgram: the plan -- what's audited, and whether it recurs.
- InternalAudit: one actual audit occurrence under a program.
- AuditFinding: one thing found during an audit.

No CAIGO-style approval workflow here -- these are operational records,
gated only by ordinary edit permission, the same way creating (not
approving) a Policy or a RiskAssessment already works.

A recurring program's next_due_date is computed, never stored, matching
risk_scoring.is_overdue / corrective_action_service.is_overdue -- it can't
silently disagree with the audit history it's derived from.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import audit_schedule
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError
from app.models.audit_finding import AuditFinding
from app.models.audit_program import AuditProgram, AuditProgramStatus, AuditScheduleType
from app.models.internal_audit import InternalAudit, InternalAuditStatus
from app.repositories import internal_audit_repository
from app.schemas.internal_audit import (
    AuditFindingCreate,
    AuditFindingUpdate,
    AuditProgramCreate,
    AuditProgramUpdate,
    InternalAuditCreate,
    InternalAuditUpdate,
)
from app.services import audit_service, evidence_service, framework_service

PROGRAM_ENTITY_TYPE = "AuditProgram"
AUDIT_ENTITY_TYPE = "InternalAudit"

# Editable directly through update_internal_audit; reaching completed goes
# through complete_internal_audit instead.
_AUDIT_EDITABLE_STATUSES = {InternalAuditStatus.PLANNED, InternalAuditStatus.IN_PROGRESS}


# ---------- computed schedule ----------


def next_due_date(program: AuditProgram, audits: list[InternalAudit]) -> date | None:
    """None for an ad hoc or archived program -- there is nothing to be due.
    Before any audit has been completed, the first cycle is simply due on
    start_date itself -- that's the planned first audit, not something to
    count another interval forward from. Once one is completed, the next
    cycle is interval_months on from its conducted_date."""
    if program.schedule_type != AuditScheduleType.INTERVAL:
        return None
    if program.status == AuditProgramStatus.ARCHIVED:
        return None
    if program.interval_months is None:
        return None

    completed_dates = [
        a.conducted_date
        for a in audits
        if a.status == InternalAuditStatus.COMPLETED and a.conducted_date
    ]
    if not completed_dates:
        return program.start_date
    return audit_schedule.next_audit_date(max(completed_dates), program.interval_months)


def is_overdue(
    program: AuditProgram, audits: list[InternalAudit], today: date | None = None
) -> bool:
    reference = today if today is not None else datetime.now(UTC).date()
    return audit_schedule.is_audit_overdue(next_due_date(program, audits), reference)


def is_audit_overdue(audit: InternalAudit, today: date | None = None) -> bool:
    """A single audit is overdue when it's still planned/in progress past
    its own planned date -- a narrower, per-occurrence sense of overdue than
    the program's next_due_date."""
    reference = today if today is not None else datetime.now(UTC).date()
    return audit.status != InternalAuditStatus.COMPLETED and audit.planned_date < reference


# ---------- audit programs ----------


def _get_program_or_raise(db: Session, program_id: int) -> AuditProgram:
    program = internal_audit_repository.get_program(db, program_id)
    if program is None:
        raise NotFoundError("AuditProgram", program_id)
    return program


def list_audit_programs(db: Session) -> list[AuditProgram]:
    return internal_audit_repository.list_programs(db)


def get_audit_program(db: Session, program_id: int) -> AuditProgram:
    return _get_program_or_raise(db, program_id)


def create_audit_program(
    db: Session, data: AuditProgramCreate, actor_id: int | None
) -> AuditProgram:
    program = AuditProgram(
        title=data.title,
        description=data.description,
        schedule_type=data.schedule_type,
        interval_months=data.interval_months,
        start_date=data.start_date,
        owner_id=data.owner_id,
        status=AuditProgramStatus.ACTIVE,
    )
    program = internal_audit_repository.create_program(db, program)
    audit_service.log(
        db, PROGRAM_ENTITY_TYPE, program.id, "created", actor_id, {"title": program.title}
    )
    return program


def update_audit_program(
    db: Session, program_id: int, data: AuditProgramUpdate, actor_id: int | None
) -> AuditProgram:
    program = _get_program_or_raise(db, program_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(program, field, value)
    if program.schedule_type == AuditScheduleType.AD_HOC:
        program.interval_months = None

    program = internal_audit_repository.save_program(db, program)
    audit_service.log(db, PROGRAM_ENTITY_TYPE, program.id, "updated", actor_id, changes)
    return program


def delete_audit_program(db: Session, program_id: int, actor_id: int | None) -> None:
    program = _get_program_or_raise(db, program_id)
    for audit in internal_audit_repository.list_for_program(db, program_id):
        _delete_audit_children(db, audit)
        internal_audit_repository.delete_audit(db, audit)
    evidence_service.delete_all_for_entity(db, PROGRAM_ENTITY_TYPE, program_id)
    framework_service.delete_tags(db, PROGRAM_ENTITY_TYPE, program_id)
    internal_audit_repository.delete_program(db, program)
    audit_service.log(db, PROGRAM_ENTITY_TYPE, program_id, "deleted", actor_id)


# ---------- internal audits ----------


def _get_audit_or_raise(db: Session, program_id: int, audit_id: int) -> InternalAudit:
    audit = internal_audit_repository.get_audit(db, audit_id)
    if audit is None or audit.audit_program_id != program_id:
        raise NotFoundError("InternalAudit", audit_id)
    return audit


def list_for_program(db: Session, program_id: int) -> list[InternalAudit]:
    _get_program_or_raise(db, program_id)
    return internal_audit_repository.list_for_program(db, program_id)


def get_internal_audit(db: Session, program_id: int, audit_id: int) -> InternalAudit:
    return _get_audit_or_raise(db, program_id, audit_id)


def create_internal_audit(
    db: Session, program_id: int, data: InternalAuditCreate, actor_id: int | None
) -> InternalAudit:
    _get_program_or_raise(db, program_id)
    audit = InternalAudit(
        audit_program_id=program_id,
        title=data.title,
        planned_date=data.planned_date,
        auditor_id=data.auditor_id,
        scope=data.scope,
        status=InternalAuditStatus.PLANNED,
    )
    audit = internal_audit_repository.create_audit(db, audit)
    audit_service.log(db, AUDIT_ENTITY_TYPE, audit.id, "created", actor_id, {"title": audit.title})
    return audit


def update_internal_audit(
    db: Session, program_id: int, audit_id: int, data: InternalAuditUpdate, actor_id: int | None
) -> InternalAudit:
    audit = _get_audit_or_raise(db, program_id, audit_id)
    if audit.status not in _AUDIT_EDITABLE_STATUSES:
        raise InvalidStatusTransitionError(
            f"InternalAudit {audit_id} cannot be edited while status is '{audit.status}'."
        )
    changes = data.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] == InternalAuditStatus.COMPLETED:
        raise InvalidStatusTransitionError(
            "Use complete_internal_audit to mark an audit completed."
        )
    for field, value in changes.items():
        setattr(audit, field, value)

    audit = internal_audit_repository.save_audit(db, audit)
    audit_service.log(db, AUDIT_ENTITY_TYPE, audit.id, "updated", actor_id, changes)
    return audit


def complete_internal_audit(
    db: Session,
    program_id: int,
    audit_id: int,
    actor_id: int | None,
    conducted_date: date | None = None,
    conclusion: str | None = None,
) -> InternalAudit:
    audit = _get_audit_or_raise(db, program_id, audit_id)
    if audit.status == InternalAuditStatus.COMPLETED:
        raise InvalidStatusTransitionError(f"InternalAudit {audit_id} is already completed.")

    audit.status = InternalAuditStatus.COMPLETED
    audit.conducted_date = conducted_date or datetime.now(UTC).date()
    if conclusion is not None:
        audit.conclusion = conclusion

    audit = internal_audit_repository.save_audit(db, audit)
    audit_service.log(db, AUDIT_ENTITY_TYPE, audit.id, "completed", actor_id)
    return audit


def _delete_audit_children(db: Session, audit: InternalAudit) -> None:
    for finding in internal_audit_repository.list_for_audit(db, audit.id):
        internal_audit_repository.delete_finding(db, finding)
    evidence_service.delete_all_for_entity(db, AUDIT_ENTITY_TYPE, audit.id)


def delete_internal_audit(
    db: Session, program_id: int, audit_id: int, actor_id: int | None
) -> None:
    audit = _get_audit_or_raise(db, program_id, audit_id)
    _delete_audit_children(db, audit)
    internal_audit_repository.delete_audit(db, audit)
    audit_service.log(db, AUDIT_ENTITY_TYPE, audit_id, "deleted", actor_id)


# ---------- audit findings ----------


def _get_finding_or_raise(db: Session, audit_id: int, finding_id: int) -> AuditFinding:
    finding = internal_audit_repository.get_finding(db, finding_id)
    if finding is None or finding.internal_audit_id != audit_id:
        raise NotFoundError("AuditFinding", finding_id)
    return finding


def list_for_audit(db: Session, program_id: int, audit_id: int) -> list[AuditFinding]:
    _get_audit_or_raise(db, program_id, audit_id)
    return internal_audit_repository.list_for_audit(db, audit_id)


def create_finding(
    db: Session, program_id: int, audit_id: int, data: AuditFindingCreate, actor_id: int | None
) -> AuditFinding:
    _get_audit_or_raise(db, program_id, audit_id)
    finding = AuditFinding(
        internal_audit_id=audit_id,
        description=data.description,
        finding_type=data.finding_type,
    )
    finding = internal_audit_repository.create_finding(db, finding)
    audit_service.log(
        db, AUDIT_ENTITY_TYPE, audit_id, "finding_added", actor_id, {"finding_id": finding.id}
    )
    return finding


def update_finding(
    db: Session,
    program_id: int,
    audit_id: int,
    finding_id: int,
    data: AuditFindingUpdate,
    actor_id: int | None,
) -> AuditFinding:
    _get_audit_or_raise(db, program_id, audit_id)
    finding = _get_finding_or_raise(db, audit_id, finding_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(finding, field, value)
    finding = internal_audit_repository.save_finding(db, finding)
    audit_service.log(
        db,
        AUDIT_ENTITY_TYPE,
        audit_id,
        "finding_updated",
        actor_id,
        {"finding_id": finding_id, **changes},
    )
    return finding


def delete_finding(
    db: Session, program_id: int, audit_id: int, finding_id: int, actor_id: int | None
) -> None:
    _get_audit_or_raise(db, program_id, audit_id)
    finding = _get_finding_or_raise(db, audit_id, finding_id)
    internal_audit_repository.delete_finding(db, finding)
    audit_service.log(
        db, AUDIT_ENTITY_TYPE, audit_id, "finding_deleted", actor_id, {"finding_id": finding_id}
    )
