from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.ai_incident import AIIncident
from app.schemas.ai_incident import AIIncidentCreate, AIIncidentRead, AIIncidentUpdate
from app.services import ai_incident_service, corrective_action_service, framework_service

router = APIRouter(prefix="/ai-incidents", tags=["ai-incidents"])


def _to_read(db: Session, incident: AIIncident) -> AIIncidentRead:
    corrective_actions = corrective_action_service.list_for_source(
        db, ai_incident_service.ENTITY_TYPE, incident.id
    )
    return AIIncidentRead(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        ai_system_row_id=incident.ai_system_row_id,
        detected_on=incident.detected_on,
        occurred_on=incident.occurred_on,
        severity=incident.severity,
        status=incident.status,
        owner_id=incident.owner_id,
        impact_description=incident.impact_description,
        immediate_actions=incident.immediate_actions,
        root_cause=incident.root_cause,
        is_serious=incident.is_serious,
        serious_category=incident.serious_category,
        authority_notified_on=incident.authority_notified_on,
        authority_reference=incident.authority_reference,
        reporting_deadline=ai_incident_service.reporting_deadline(incident),
        reporting_overdue=ai_incident_service.is_reporting_overdue(incident),
        corrective_action_ids=[ca.id for ca in corrective_actions],
        framework_tags=framework_service.get_tags(db, ai_incident_service.ENTITY_TYPE, incident.id),
        resolved_at=incident.resolved_at,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


@router.get("", response_model=list[AIIncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[AIIncidentRead]:
    return [_to_read(db, incident) for incident in ai_incident_service.list_incidents(db)]


@router.post("", response_model=AIIncidentRead, status_code=201)
def create_incident(
    data: AIIncidentCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AIIncidentRead:
    return _to_read(db, ai_incident_service.create_incident(db, data, actor_id))


@router.get("/{incident_id}", response_model=AIIncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> AIIncidentRead:
    return _to_read(db, ai_incident_service.get_incident(db, incident_id))


@router.put("/{incident_id}", response_model=AIIncidentRead)
def update_incident(
    incident_id: int,
    data: AIIncidentUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AIIncidentRead:
    return _to_read(db, ai_incident_service.update_incident(db, incident_id, data, actor_id))


@router.delete("/{incident_id}", status_code=204)
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    ai_incident_service.delete_incident(db, incident_id, actor_id)
