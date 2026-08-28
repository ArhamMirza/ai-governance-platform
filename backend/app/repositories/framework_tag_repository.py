from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.framework_control import FrameworkControl
from app.models.framework_tag import FrameworkTag
from app.repositories.framework_control_repository import _natural_code_key


def list_controls_for_entity(
    db: Session, entity_type: str, entity_id: int
) -> list[FrameworkControl]:
    query = (
        select(FrameworkControl)
        .join(FrameworkTag, FrameworkTag.framework_control_id == FrameworkControl.id)
        .where(FrameworkTag.entity_type == entity_type, FrameworkTag.entity_id == entity_id)
    )
    return sorted(db.scalars(query), key=_natural_code_key)


def list_all_grouped_by_control(db: Session) -> dict[int, list[FrameworkTag]]:
    """All tags, grouped by the control they're tagged against -- the raw
    material for the clause-mapping and SoA views (which entity is tagged to
    each clause/control)."""
    grouped: dict[int, list[FrameworkTag]] = {}
    for tag in db.scalars(select(FrameworkTag)):
        grouped.setdefault(tag.framework_control_id, []).append(tag)
    return grouped


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
