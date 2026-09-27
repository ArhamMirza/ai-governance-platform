from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.audit_finding import AuditFinding
from app.models.audit_program import AuditProgram
from app.models.internal_audit import InternalAudit
from app.schemas.internal_audit import (
    AuditFindingCreate,
    AuditFindingRead,
    AuditFindingUpdate,
    AuditProgramCreate,
    AuditProgramRead,
    AuditProgramUpdate,
    InternalAuditCreate,
    InternalAuditRead,
    InternalAuditUpdate,
)
from app.services import corrective_action_service, framework_service, internal_audit_service

router = APIRouter(prefix="/audit-programs", tags=["internal-audits"])


def _program_to_read(db: Session, program: AuditProgram) -> AuditProgramRead:
    audits = internal_audit_service.list_for_program(db, program.id)
    framework_tags = framework_service.get_tags(
        db, internal_audit_service.PROGRAM_ENTITY_TYPE, program.id
    )
    return AuditProgramRead(
        id=program.id,
        title=program.title,
        description=program.description,
        schedule_type=program.schedule_type,
        interval_months=program.interval_months,
        start_date=program.start_date,
        owner_id=program.owner_id,
        status=program.status,
        next_due_date=internal_audit_service.next_due_date(program, audits),
        overdue=internal_audit_service.is_overdue(program, audits, datetime.now(UTC).date()),
        framework_tags=framework_tags,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


def _audit_to_read(audit: InternalAudit) -> InternalAuditRead:
    return InternalAuditRead(
        id=audit.id,
        audit_program_id=audit.audit_program_id,
        title=audit.title,
        planned_date=audit.planned_date,
        conducted_date=audit.conducted_date,
        auditor_id=audit.auditor_id,
        scope=audit.scope,
        conclusion=audit.conclusion,
        status=audit.status,
        overdue=internal_audit_service.is_audit_overdue(audit, datetime.now(UTC).date()),
        created_at=audit.created_at,
        updated_at=audit.updated_at,
    )


def _finding_to_read(db: Session, finding: AuditFinding) -> AuditFindingRead:
    corrective_actions = corrective_action_service.list_for_source(db, "AuditFinding", finding.id)
    return AuditFindingRead(
        id=finding.id,
        internal_audit_id=finding.internal_audit_id,
        description=finding.description,
        finding_type=finding.finding_type,
        corrective_action_ids=[ca.id for ca in corrective_actions],
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )


# ---------- audit programs ----------


@router.get("", response_model=list[AuditProgramRead])
def list_audit_programs(db: Session = Depends(get_db)) -> list[AuditProgramRead]:
    return [_program_to_read(db, p) for p in internal_audit_service.list_audit_programs(db)]


@router.post("", response_model=AuditProgramRead, status_code=201)
def create_audit_program(
    data: AuditProgramCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AuditProgramRead:
    program = internal_audit_service.create_audit_program(db, data, actor_id)
    return _program_to_read(db, program)


@router.get("/{program_id}", response_model=AuditProgramRead)
def get_audit_program(program_id: int, db: Session = Depends(get_db)) -> AuditProgramRead:
    return _program_to_read(db, internal_audit_service.get_audit_program(db, program_id))


@router.put("/{program_id}", response_model=AuditProgramRead)
def update_audit_program(
    program_id: int,
    data: AuditProgramUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AuditProgramRead:
    program = internal_audit_service.update_audit_program(db, program_id, data, actor_id)
    return _program_to_read(db, program)


@router.delete("/{program_id}", status_code=204)
def delete_audit_program(
    program_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    internal_audit_service.delete_audit_program(db, program_id, actor_id)


# ---------- internal audits ----------


@router.get("/{program_id}/audits", response_model=list[InternalAuditRead])
def list_internal_audits(program_id: int, db: Session = Depends(get_db)) -> list[InternalAuditRead]:
    return [_audit_to_read(a) for a in internal_audit_service.list_for_program(db, program_id)]


@router.post("/{program_id}/audits", response_model=InternalAuditRead, status_code=201)
def create_internal_audit(
    program_id: int,
    data: InternalAuditCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> InternalAuditRead:
    audit = internal_audit_service.create_internal_audit(db, program_id, data, actor_id)
    return _audit_to_read(audit)


@router.get("/{program_id}/audits/{audit_id}", response_model=InternalAuditRead)
def get_internal_audit(
    program_id: int, audit_id: int, db: Session = Depends(get_db)
) -> InternalAuditRead:
    return _audit_to_read(internal_audit_service.get_internal_audit(db, program_id, audit_id))


@router.put("/{program_id}/audits/{audit_id}", response_model=InternalAuditRead)
def update_internal_audit(
    program_id: int,
    audit_id: int,
    data: InternalAuditUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> InternalAuditRead:
    audit = internal_audit_service.update_internal_audit(db, program_id, audit_id, data, actor_id)
    return _audit_to_read(audit)


@router.delete("/{program_id}/audits/{audit_id}", status_code=204)
def delete_internal_audit(
    program_id: int,
    audit_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    internal_audit_service.delete_internal_audit(db, program_id, audit_id, actor_id)


@router.post("/{program_id}/audits/{audit_id}/complete", response_model=InternalAuditRead)
def complete_internal_audit(
    program_id: int,
    audit_id: int,
    conducted_date: date | None = None,
    conclusion: str | None = None,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> InternalAuditRead:
    audit = internal_audit_service.complete_internal_audit(
        db, program_id, audit_id, actor_id, conducted_date=conducted_date, conclusion=conclusion
    )
    return _audit_to_read(audit)


# ---------- audit findings ----------


@router.get("/{program_id}/audits/{audit_id}/findings", response_model=list[AuditFindingRead])
def list_audit_findings(
    program_id: int, audit_id: int, db: Session = Depends(get_db)
) -> list[AuditFindingRead]:
    return [
        _finding_to_read(db, f)
        for f in internal_audit_service.list_for_audit(db, program_id, audit_id)
    ]


@router.post(
    "/{program_id}/audits/{audit_id}/findings", response_model=AuditFindingRead, status_code=201
)
def create_audit_finding(
    program_id: int,
    audit_id: int,
    data: AuditFindingCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AuditFindingRead:
    finding = internal_audit_service.create_finding(db, program_id, audit_id, data, actor_id)
    return _finding_to_read(db, finding)


@router.put(
    "/{program_id}/audits/{audit_id}/findings/{finding_id}", response_model=AuditFindingRead
)
def update_audit_finding(
    program_id: int,
    audit_id: int,
    finding_id: int,
    data: AuditFindingUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AuditFindingRead:
    finding = internal_audit_service.update_finding(
        db, program_id, audit_id, finding_id, data, actor_id
    )
    return _finding_to_read(db, finding)


@router.delete("/{program_id}/audits/{audit_id}/findings/{finding_id}", status_code=204)
def delete_audit_finding(
    program_id: int,
    audit_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    internal_audit_service.delete_finding(db, program_id, audit_id, finding_id, actor_id)
