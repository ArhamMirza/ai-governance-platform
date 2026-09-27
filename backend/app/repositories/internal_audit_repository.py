from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_finding import AuditFinding
from app.models.audit_program import AuditProgram
from app.models.internal_audit import InternalAudit

# ---------- audit programs ----------


def get_program(db: Session, program_id: int) -> AuditProgram | None:
    return db.get(AuditProgram, program_id)


def list_programs(db: Session) -> list[AuditProgram]:
    return list(db.scalars(select(AuditProgram).order_by(AuditProgram.id)))


def create_program(db: Session, program: AuditProgram) -> AuditProgram:
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


def save_program(db: Session, program: AuditProgram) -> AuditProgram:
    db.commit()
    db.refresh(program)
    return program


def delete_program(db: Session, program: AuditProgram) -> None:
    db.delete(program)
    db.commit()


# ---------- internal audits ----------


def get_audit(db: Session, audit_id: int) -> InternalAudit | None:
    return db.get(InternalAudit, audit_id)


def list_for_program(db: Session, program_id: int) -> list[InternalAudit]:
    return list(
        db.scalars(
            select(InternalAudit)
            .where(InternalAudit.audit_program_id == program_id)
            .order_by(InternalAudit.planned_date)
        )
    )


def create_audit(db: Session, audit: InternalAudit) -> InternalAudit:
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def save_audit(db: Session, audit: InternalAudit) -> InternalAudit:
    db.commit()
    db.refresh(audit)
    return audit


def delete_audit(db: Session, audit: InternalAudit) -> None:
    db.delete(audit)
    db.commit()


# ---------- audit findings ----------


def get_finding(db: Session, finding_id: int) -> AuditFinding | None:
    return db.get(AuditFinding, finding_id)


def list_for_audit(db: Session, internal_audit_id: int) -> list[AuditFinding]:
    return list(
        db.scalars(
            select(AuditFinding)
            .where(AuditFinding.internal_audit_id == internal_audit_id)
            .order_by(AuditFinding.id)
        )
    )


def create_finding(db: Session, finding: AuditFinding) -> AuditFinding:
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def save_finding(db: Session, finding: AuditFinding) -> AuditFinding:
    db.commit()
    db.refresh(finding)
    return finding


def delete_finding(db: Session, finding: AuditFinding) -> None:
    db.delete(finding)
    db.commit()
