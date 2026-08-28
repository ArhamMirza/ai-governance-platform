"""Framework control reference data and entity tagging.

Tags are polymorphic (entity_type + entity_id, same pattern as the audit log)
so Policy, Procedure, RiskAssessment, and Evidence share one tagging
mechanism instead of each carrying their own free-text column.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.evidence import Evidence
from app.models.framework_control import FrameworkControl
from app.models.framework_soa_entry import SoaApplicability
from app.models.framework_tag import FrameworkTag
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.models.risk_assessment import RiskAssessment
from app.repositories import (
    framework_control_repository,
    framework_soa_repository,
    framework_tag_repository,
)
from app.schemas.framework_control import (
    FrameworkMappingEntry,
    FrameworkSoaEntryRead,
    TaggedItem,
)
from app.services import audit_service

ACTION = "framework_tags_updated"
SOA_ACTION = "framework_soa_updated"

_VALID_APPLICABILITY = {SoaApplicability.APPLICABLE, SoaApplicability.NOT_APPLICABLE}


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


def _resolve_label(db: Session, entity_type: str, entity_id: int) -> str:
    """Human-readable label for a tagged entity, for the mapping/SoA views."""
    if entity_type == "Policy":
        policy = db.get(Policy, entity_id)
        if policy is not None:
            return policy.title
    elif entity_type == "Procedure":
        procedure = db.get(Procedure, entity_id)
        if procedure is not None:
            return procedure.title
    elif entity_type == "Evidence":
        evidence = db.get(Evidence, entity_id)
        if evidence is not None:
            return evidence.filename
    elif entity_type == "RiskAssessment":
        risk_assessment = db.get(RiskAssessment, entity_id)
        if risk_assessment is not None:
            return f"Risk Assessment #{risk_assessment.id}"
    return f"{entity_type} #{entity_id}"


def _tagged_items_for_control(
    db: Session, control_id: int, tags_by_control: dict[int, list[FrameworkTag]]
) -> list[TaggedItem]:
    return [
        TaggedItem(
            entity_type=tag.entity_type,
            entity_id=tag.entity_id,
            label=_resolve_label(db, tag.entity_type, tag.entity_id),
        )
        for tag in tags_by_control.get(control_id, [])
    ]


def get_mapping(db: Session, framework: str | None = None) -> list[FrameworkMappingEntry]:
    controls = framework_control_repository.list_all(db, framework)
    tags_by_control = framework_tag_repository.list_all_grouped_by_control(db)
    return [
        FrameworkMappingEntry(
            id=control.id,
            framework=control.framework,
            code=control.code,
            title=control.title,
            description=control.description,
            category=control.category,
            tagged_items=_tagged_items_for_control(db, control.id, tags_by_control),
        )
        for control in controls
    ]


def get_soa(db: Session) -> list[FrameworkSoaEntryRead]:
    controls = framework_control_repository.list_all(
        db, framework="iso_42001", category="annex_a_control"
    )
    entries_by_control = {
        entry.framework_control_id: entry for entry in framework_soa_repository.list_all(db)
    }
    tags_by_control = framework_tag_repository.list_all_grouped_by_control(db)

    results = []
    for control in controls:
        entry = entries_by_control.get(control.id)
        results.append(
            FrameworkSoaEntryRead(
                id=control.id,
                framework=control.framework,
                code=control.code,
                title=control.title,
                description=control.description,
                applicability=entry.applicability if entry else SoaApplicability.APPLICABLE,
                justification=entry.justification if entry else None,
                updated_at=entry.updated_at if entry else datetime.now(UTC),
                tagged_items=_tagged_items_for_control(db, control.id, tags_by_control),
            )
        )
    return results


def update_soa_entry(
    db: Session,
    control_id: int,
    applicability: str,
    justification: str | None,
    actor_id: int | None,
) -> FrameworkSoaEntryRead:
    if applicability not in _VALID_APPLICABILITY:
        raise ValidationError(f"Invalid applicability: {applicability}")

    control = framework_control_repository.get_by_id(db, control_id)
    if control is None or control.category != "annex_a_control":
        raise NotFoundError("Annex A control", control_id)

    framework_soa_repository.upsert(db, control_id, applicability, justification, actor_id)
    audit_service.log(
        db,
        "FrameworkSoaEntry",
        control_id,
        SOA_ACTION,
        actor_id,
        {"applicability": applicability, "justification": justification},
    )

    tags_by_control = framework_tag_repository.list_all_grouped_by_control(db)
    entry = framework_soa_repository.get_by_control_id(db, control_id)
    return FrameworkSoaEntryRead(
        id=control.id,
        framework=control.framework,
        code=control.code,
        title=control.title,
        description=control.description,
        applicability=entry.applicability,
        justification=entry.justification,
        updated_at=entry.updated_at,
        tagged_items=_tagged_items_for_control(db, control.id, tags_by_control),
    )
