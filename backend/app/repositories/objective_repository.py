from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_objective import AIObjective
from app.models.ai_objective_ai_system import AIObjectiveAISystem
from app.models.objective_measurement import ObjectiveMeasurement


def get(db: Session, objective_id: int) -> AIObjective | None:
    return db.get(AIObjective, objective_id)


def list_all(db: Session) -> list[AIObjective]:
    return list(db.scalars(select(AIObjective).order_by(AIObjective.title, AIObjective.id)))


def list_for_policy(db: Session, policy_id: int) -> list[AIObjective]:
    return list(
        db.scalars(
            select(AIObjective).where(AIObjective.policy_id == policy_id).order_by(AIObjective.id)
        )
    )


def create(db: Session, objective: AIObjective) -> AIObjective:
    db.add(objective)
    db.commit()
    db.refresh(objective)
    return objective


def save(db: Session, objective: AIObjective) -> AIObjective:
    db.commit()
    db.refresh(objective)
    return objective


def delete(db: Session, objective: AIObjective) -> None:
    db.delete(objective)
    db.commit()


def get_measurement(db: Session, measurement_id: int) -> ObjectiveMeasurement | None:
    return db.get(ObjectiveMeasurement, measurement_id)


def list_measurements(db: Session) -> list[ObjectiveMeasurement]:
    """Every reading, in the order recorded."""
    return list(db.scalars(select(ObjectiveMeasurement).order_by(ObjectiveMeasurement.id)))


def list_measurements_for_objective(db: Session, objective_id: int) -> list[ObjectiveMeasurement]:
    """In the order recorded -- objective_tracking.standing relies on it to
    pick the later of two readings taken the same day."""
    return list(
        db.scalars(
            select(ObjectiveMeasurement)
            .where(ObjectiveMeasurement.objective_id == objective_id)
            .order_by(ObjectiveMeasurement.id)
        )
    )


def create_measurement(db: Session, measurement: ObjectiveMeasurement) -> ObjectiveMeasurement:
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


def delete_measurement(db: Session, measurement: ObjectiveMeasurement) -> None:
    db.delete(measurement)
    db.commit()


def list_links(db: Session) -> list[AIObjectiveAISystem]:
    return list(db.scalars(select(AIObjectiveAISystem).order_by(AIObjectiveAISystem.id)))


def list_links_for_objective(db: Session, objective_id: int) -> list[AIObjectiveAISystem]:
    return list(
        db.scalars(
            select(AIObjectiveAISystem)
            .where(AIObjectiveAISystem.objective_id == objective_id)
            .order_by(AIObjectiveAISystem.ai_system_row_id)
        )
    )


def list_links_for_ai_system(db: Session, ai_system_row_id: int) -> list[AIObjectiveAISystem]:
    return list(
        db.scalars(
            select(AIObjectiveAISystem)
            .where(AIObjectiveAISystem.ai_system_row_id == ai_system_row_id)
            .order_by(AIObjectiveAISystem.objective_id)
        )
    )


def replace_links(db: Session, objective_id: int, ai_system_row_ids: list[int]) -> None:
    """Makes the objective's links exactly this set, in one commit, keeping
    the ones that survive rather than deleting and recreating them."""
    wanted = set(ai_system_row_ids)
    existing = {link.ai_system_row_id: link for link in list_links_for_objective(db, objective_id)}
    for row_id, link in existing.items():
        if row_id not in wanted:
            db.delete(link)
    for row_id in sorted(wanted - existing.keys()):
        db.add(AIObjectiveAISystem(objective_id=objective_id, ai_system_row_id=row_id))
    db.commit()


def delete_links(db: Session, links: list[AIObjectiveAISystem]) -> None:
    for link in links:
        db.delete(link)
    db.commit()
