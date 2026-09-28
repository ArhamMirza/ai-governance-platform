from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competence_record import CompetenceRecord
from app.models.competence_requirement import CompetenceRequirement


def get_requirement(db: Session, requirement_id: int) -> CompetenceRequirement | None:
    return db.get(CompetenceRequirement, requirement_id)


def list_requirements(db: Session) -> list[CompetenceRequirement]:
    return list(db.scalars(select(CompetenceRequirement).order_by(CompetenceRequirement.id)))


def list_requirements_for_role(db: Session, role_id: int) -> list[CompetenceRequirement]:
    return list(
        db.scalars(
            select(CompetenceRequirement)
            .where(CompetenceRequirement.governance_role_id == role_id)
            .order_by(CompetenceRequirement.id)
        )
    )


def create_requirement(db: Session, requirement: CompetenceRequirement) -> CompetenceRequirement:
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def save_requirement(db: Session, requirement: CompetenceRequirement) -> CompetenceRequirement:
    db.commit()
    db.refresh(requirement)
    return requirement


def delete_requirement(db: Session, requirement: CompetenceRequirement) -> None:
    db.delete(requirement)
    db.commit()


def get_record(db: Session, record_id: int) -> CompetenceRecord | None:
    return db.get(CompetenceRecord, record_id)


def list_records(db: Session) -> list[CompetenceRecord]:
    return list(db.scalars(select(CompetenceRecord).order_by(CompetenceRecord.id)))


def list_records_for_requirement(db: Session, requirement_id: int) -> list[CompetenceRecord]:
    return list(
        db.scalars(
            select(CompetenceRecord)
            .where(CompetenceRecord.requirement_id == requirement_id)
            .order_by(CompetenceRecord.completed_on.desc(), CompetenceRecord.id.desc())
        )
    )


def create_record(db: Session, record: CompetenceRecord) -> CompetenceRecord:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: CompetenceRecord) -> None:
    db.delete(record)
    db.commit()
