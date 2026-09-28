from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_incident import AIIncident


def get(db: Session, incident_id: int) -> AIIncident | None:
    return db.get(AIIncident, incident_id)


def list_all(db: Session) -> list[AIIncident]:
    return list(db.scalars(select(AIIncident).order_by(AIIncident.id)))


def list_for_ai_system(db: Session, ai_system_row_id: int) -> list[AIIncident]:
    return list(
        db.scalars(
            select(AIIncident)
            .where(AIIncident.ai_system_row_id == ai_system_row_id)
            .order_by(AIIncident.id)
        )
    )


def create(db: Session, incident: AIIncident) -> AIIncident:
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def save(db: Session, incident: AIIncident) -> AIIncident:
    db.commit()
    db.refresh(incident)
    return incident


def delete(db: Session, incident: AIIncident) -> None:
    db.delete(incident)
    db.commit()
