"""Framework control reference data and entity tagging.

Tags are polymorphic (entity_type + entity_id, same pattern as the audit log)
so Policy, Procedure, and RiskAssessment share one tagging mechanism instead
of each carrying their own free-text column.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.framework_control import FrameworkControl
from app.repositories import framework_control_repository, framework_tag_repository
from app.services import audit_service

ACTION = "framework_tags_updated"


def list_controls(db: Session, framework: str | None = None) -> list[FrameworkControl]:
    return framework_control_repository.list_all(db, framework)


def get_tags(db: Session, entity_type: str, entity_id: int) -> list[FrameworkControl]:
    return framework_tag_repository.list_controls_for_entity(db, entity_type, entity_id)


def set_tags(
    db: Session,
    entity_type: str,
    entity_id: int,
    control_ids: list[int],
    actor_id: int | None,
) -> list[FrameworkControl]:
    unique_ids = list(dict.fromkeys(control_ids))
    found = framework_control_repository.list_by_ids(db, unique_ids)
    if len(found) != len(unique_ids):
        missing = set(unique_ids) - {control.id for control in found}
        raise ValidationError(f"Unknown framework control id(s): {sorted(missing)}")

    framework_tag_repository.replace_for_entity(db, entity_type, entity_id, unique_ids)
    audit_service.log(
        db, entity_type, entity_id, ACTION, actor_id, {"control_ids": unique_ids}
    )
    return get_tags(db, entity_type, entity_id)


def delete_tags(db: Session, entity_type: str, entity_id: int) -> None:
    """Called when the tagged entity itself is deleted."""
    framework_tag_repository.delete_for_entity(db, entity_type, entity_id)
