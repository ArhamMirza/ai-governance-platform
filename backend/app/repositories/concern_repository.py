from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.concern import Concern, ConcernSettings


def get(db: Session, concern_id: int) -> Concern | None:
    return db.get(Concern, concern_id)


def list_all(db: Session) -> list[Concern]:
    return list(db.scalars(select(Concern).order_by(Concern.received_on.desc(), Concern.id.desc())))


def list_for_reporter(db: Session, reporter_id: int) -> list[Concern]:
    return list(
        db.scalars(
            select(Concern)
            .where(Concern.reporter_id == reporter_id)
            .order_by(Concern.received_on.desc(), Concern.id.desc())
        )
    )


def get_by_code_hash(db: Session, code_hash: str) -> Concern | None:
    return db.scalar(select(Concern).where(Concern.tracking_code_hash == code_hash))


def list_for_ai_system(db: Session, ai_system_row_id: int) -> list[Concern]:
    return list(db.scalars(select(Concern).where(Concern.ai_system_row_id == ai_system_row_id)))


def create(db: Session, concern: Concern) -> Concern:
    db.add(concern)
    db.commit()
    db.refresh(concern)
    return concern


def save(db: Session, concern: Concern) -> Concern:
    db.commit()
    db.refresh(concern)
    return concern


def get_settings(db: Session) -> ConcernSettings | None:
    return db.scalar(select(ConcernSettings).order_by(ConcernSettings.id))


def create_settings(db: Session, settings: ConcernSettings) -> ConcernSettings:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save_settings(db: Session, settings: ConcernSettings) -> ConcernSettings:
    db.commit()
    db.refresh(settings)
    return settings
