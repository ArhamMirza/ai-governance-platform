from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence


def get(db: Session, evidence_id: int) -> Evidence | None:
    return db.get(Evidence, evidence_id)


def list_at_level(
    db: Session, entity_type: str, entity_id: int, folder_id: int | None
) -> list[Evidence]:
    return list(
        db.scalars(
            select(Evidence)
            .where(
                Evidence.entity_type == entity_type,
                Evidence.entity_id == entity_id,
                Evidence.folder_id == folder_id,
            )
            .order_by(Evidence.filename)
        )
    )


def list_for_entity(
    db: Session, entity_type: str, entity_id: int, document_type: str | None = None
) -> list[Evidence]:
    """Every document for an entity regardless of folder -- list_at_level is
    single-level, but a stage gate doesn't care where the file was filed."""
    query = select(Evidence).where(
        Evidence.entity_type == entity_type, Evidence.entity_id == entity_id
    )
    if document_type is not None:
        query = query.where(Evidence.document_type == document_type)
    return list(db.scalars(query.order_by(Evidence.filename)))


def has_evidence_in_folder(db: Session, folder_id: int) -> bool:
    return db.scalar(select(Evidence.id).where(Evidence.folder_id == folder_id)) is not None


def create(db: Session, evidence: Evidence) -> Evidence:
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def delete(db: Session, evidence: Evidence) -> None:
    db.delete(evidence)
    db.commit()
