from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.communication import CommunicationPlanItem, CommunicationRecord


def get(db: Session, item_id: int) -> CommunicationPlanItem | None:
    return db.get(CommunicationPlanItem, item_id)


def list_all(db: Session) -> list[CommunicationPlanItem]:
    return list(
        db.scalars(
            select(CommunicationPlanItem).order_by(
                CommunicationPlanItem.topic, CommunicationPlanItem.id
            )
        )
    )


def create(db: Session, item: CommunicationPlanItem) -> CommunicationPlanItem:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def save(db: Session, item: CommunicationPlanItem) -> CommunicationPlanItem:
    db.commit()
    db.refresh(item)
    return item


def delete(db: Session, item: CommunicationPlanItem) -> None:
    db.delete(item)
    db.commit()


def get_record(db: Session, record_id: int) -> CommunicationRecord | None:
    return db.get(CommunicationRecord, record_id)


def list_records(db: Session) -> list[CommunicationRecord]:
    return list(db.scalars(select(CommunicationRecord).order_by(CommunicationRecord.id)))


def list_records_for_item(db: Session, item_id: int) -> list[CommunicationRecord]:
    return list(
        db.scalars(
            select(CommunicationRecord)
            .where(CommunicationRecord.communication_id == item_id)
            .order_by(CommunicationRecord.communicated_on.desc(), CommunicationRecord.id.desc())
        )
    )


def create_record(db: Session, record: CommunicationRecord) -> CommunicationRecord:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: CommunicationRecord) -> None:
    db.delete(record)
    db.commit()
