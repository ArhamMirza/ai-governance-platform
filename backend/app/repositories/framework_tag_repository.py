from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.framework_control import FrameworkControl
from app.models.framework_tag import FrameworkTag


def list_controls_for_entity(
    db: Session, entity_type: str, entity_id: int
) -> list[FrameworkControl]:
    query = (
        select(FrameworkControl)
        .join(FrameworkTag, FrameworkTag.framework_control_id == FrameworkControl.id)
        .where(FrameworkTag.entity_type == entity_type, FrameworkTag.entity_id == entity_id)
        .order_by(FrameworkControl.framework, FrameworkControl.code)
    )
    return list(db.scalars(query))


def replace_for_entity(
    db: Session, entity_type: str, entity_id: int, control_ids: list[int]
) -> None:
    """Set the exact tag set for an entity -- deletes anything not in control_ids."""
    existing = list(
        db.scalars(
            select(FrameworkTag).where(
                FrameworkTag.entity_type == entity_type, FrameworkTag.entity_id == entity_id
            )
        )
    )
    for tag in existing:
        db.delete(tag)
    # Without this, the unit of work can flush the new inserts before these
    # deletes, tripping the (entity_type, entity_id, framework_control_id)
    # unique constraint whenever a control id is re-tagged.
    db.flush()

    for control_id in control_ids:
        db.add(
            FrameworkTag(
                entity_type=entity_type, entity_id=entity_id, framework_control_id=control_id
            )
        )
    db.commit()


def delete_for_entity(db: Session, entity_type: str, entity_id: int) -> None:
    for tag in db.scalars(
        select(FrameworkTag).where(
            FrameworkTag.entity_type == entity_type, FrameworkTag.entity_id == entity_id
        )
    ):
        db.delete(tag)
    db.commit()
