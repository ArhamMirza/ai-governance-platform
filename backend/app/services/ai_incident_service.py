"""AI incident log -- ISO/IEC 42001 A.8.4 and EU AI Act Art. 73.

A flat, independent record gated only by ordinary edit permission, like
Internal Audit and Management Review: logging what went wrong shouldn't
wait on an approval chain. The one hard rule is Art. 73's: a serious
incident can't be marked resolved until the authority notification is
recorded (see _validate).

Remediation lives in CorrectiveAction, linked back through its
(source_type="AIIncident", source_id) pair -- see
corrective_action_service.list_for_source.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import incident_reporting
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.models.ai_incident import AIIncident, AIIncidentStatus
from app.repositories import ai_incident_repository, sheet_repository
from app.schemas.ai_incident import AIIncidentCreate, AIIncidentUpdate
from app.services import (
    ai_system_inventory_service,
    audit_service,
    corrective_action_service,
    framework_service,
)

ENTITY_TYPE = "AIIncident"


def reporting_deadline(incident: AIIncident) -> date | None:
    return incident_reporting.reporting_deadline(
        incident.is_serious, incident.serious_category, incident.detected_on
    )


def is_reporting_overdue(incident: AIIncident, today: date | None = None) -> bool:
    reference = today if today is not None else datetime.now(UTC).date()
    return incident_reporting.is_reporting_overdue(
        incident.is_serious,
        incident.serious_category,
        incident.detected_on,
        incident.authority_notified_on,
        reference,
    )


def _get_or_raise(db: Session, incident_id: int) -> AIIncident:
    incident = ai_incident_repository.get(db, incident_id)
    if incident is None:
        raise NotFoundError("AIIncident", incident_id)
    return incident


def _validate_ai_system_row(db: Session, ai_system_row_id: int | None) -> None:
    if ai_system_row_id is None:
        return
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None or row.sheet_id != inventory_sheet.id:
        raise NotFoundError("AISystemRow", ai_system_row_id)


def _validate(incident: AIIncident) -> None:
    """Checked against the incident as it will be saved, so no combination
    of fields in one update can slip past it."""
    if incident.is_serious and incident.serious_category is None:
        raise ValidationError(
            "Choose which kind of serious incident this is -- it sets the deadline "
            "for reporting it to the authority."
        )
    if (
        incident.status == AIIncidentStatus.RESOLVED
        and incident.is_serious
        and incident.authority_notified_on is None
    ):
        raise InvalidStatusTransitionError(
            "A serious incident can't be resolved until you record when the "
            "authority was notified (EU AI Act Art. 73)."
        )


def list_incidents(db: Session) -> list[AIIncident]:
    return ai_incident_repository.list_all(db)


def get_incident(db: Session, incident_id: int) -> AIIncident:
    return _get_or_raise(db, incident_id)


def create_incident(db: Session, data: AIIncidentCreate, actor_id: int | None) -> AIIncident:
    _validate_ai_system_row(db, data.ai_system_row_id)
    incident = AIIncident(
        title=data.title,
        description=data.description,
        ai_system_row_id=data.ai_system_row_id,
        detected_on=data.detected_on,
        occurred_on=data.occurred_on,
        severity=data.severity,
        status=AIIncidentStatus.OPEN,
        owner_id=data.owner_id,
        is_serious=data.is_serious,
        serious_category=data.serious_category if data.is_serious else None,
    )
    _validate(incident)
    incident = ai_incident_repository.create(db, incident)
    audit_service.log(db, ENTITY_TYPE, incident.id, "created", actor_id, {"title": incident.title})
    return incident


def update_incident(
    db: Session, incident_id: int, data: AIIncidentUpdate, actor_id: int | None
) -> AIIncident:
    incident = _get_or_raise(db, incident_id)
    changes = data.model_dump(exclude_unset=True)
    if "ai_system_row_id" in changes:
        _validate_ai_system_row(db, changes["ai_system_row_id"])

    was_resolved = incident.status == AIIncidentStatus.RESOLVED
    for field, value in changes.items():
        setattr(incident, field, value)
    if not incident.is_serious:
        incident.serious_category = None

    try:
        _validate(incident)
    except (ValidationError, InvalidStatusTransitionError):
        db.rollback()
        raise

    now_resolved = incident.status == AIIncidentStatus.RESOLVED
    if now_resolved and not was_resolved:
        incident.resolved_at = datetime.now(UTC)
    elif was_resolved and not now_resolved:
        incident.resolved_at = None

    incident = ai_incident_repository.save(db, incident)
    audit_service.log(db, ENTITY_TYPE, incident.id, "updated", actor_id, changes)
    return incident


def unlink_ai_system(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    """Clears the AI system on every incident about a system being deleted.
    The incidents themselves survive -- they're a record of what happened,
    which stays true after the system is gone."""
    for incident in ai_incident_repository.list_for_ai_system(db, ai_system_row_id):
        incident.ai_system_row_id = None
        ai_incident_repository.save(db, incident)
        audit_service.log(
            db,
            ENTITY_TYPE,
            incident.id,
            "ai_system_unlinked",
            actor_id,
            {"ai_system_row_id": ai_system_row_id},
        )


def delete_incident(db: Session, incident_id: int, actor_id: int | None) -> None:
    """Only a still-open incident with nothing raised from it can be deleted
    -- e.g. one logged twice by mistake. Anything further along is history,
    and a corrective action pointing at it would be left pointing at
    nothing."""
    # Imported here rather than at module scope, matching
    # corrective_action_service: evidence_service imports services back.
    from app.services import evidence_service

    incident = _get_or_raise(db, incident_id)
    if incident.status != AIIncidentStatus.OPEN:
        raise InvalidStatusTransitionError(
            f"AIIncident {incident_id} cannot be deleted while status is "
            f"'{incident.status}'; only a still-open incident can be deleted"
        )
    if corrective_action_service.list_for_source(db, ENTITY_TYPE, incident_id):
        raise InvalidStatusTransitionError(
            "This incident has corrective actions raised from it, so it can't be deleted."
        )
    ai_incident_repository.delete(db, incident)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, incident_id)
    framework_service.delete_tags(db, ENTITY_TYPE, incident_id)
    audit_service.log(db, ENTITY_TYPE, incident_id, "deleted", actor_id)
