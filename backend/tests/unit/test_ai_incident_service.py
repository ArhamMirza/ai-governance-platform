from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.core.incident_reporting import SeriousIncidentCategory
from app.models.ai_incident import AIIncidentStatus
from app.schemas.ai_incident import AIIncidentCreate, AIIncidentUpdate
from app.schemas.corrective_action import CorrectiveActionCreate
from app.services import (
    ai_incident_service,
    ai_system_inventory_service,
    corrective_action_service,
)


def make_ai_system(db: Session, name: str = "Resume Screener") -> int:
    return ai_system_inventory_service.add_row(db, {"name": name}, actor_id=None).id


def make_incident(db: Session, **overrides):
    data = {
        "title": "Screener rejected every applicant over 50",
        "description": "Age-correlated features drove rejections for a week.",
        "detected_on": date(2026, 3, 1),
    }
    data.update(overrides)
    return ai_incident_service.create_incident(db, AIIncidentCreate(**data), actor_id=None)


def test_create_starts_open(db_session: Session) -> None:
    incident = make_incident(db_session)

    assert incident.status == AIIncidentStatus.OPEN
    assert incident.is_serious is False
    assert ai_incident_service.reporting_deadline(incident) is None


def test_create_rejects_an_unknown_ai_system(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        make_incident(db_session, ai_system_row_id=9999)


def test_create_links_a_real_ai_system(db_session: Session) -> None:
    row_id = make_ai_system(db_session)

    assert make_incident(db_session, ai_system_row_id=row_id).ai_system_row_id == row_id


def test_a_serious_incident_needs_a_category(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        make_incident(db_session, is_serious=True)


def test_a_serious_incident_gets_a_reporting_deadline(db_session: Session) -> None:
    incident = make_incident(
        db_session, is_serious=True, serious_category=SeriousIncidentCategory.DEATH
    )

    assert ai_incident_service.reporting_deadline(incident) == date(2026, 3, 11)
    assert ai_incident_service.is_reporting_overdue(incident, date(2026, 3, 12))


def test_a_serious_incident_cannot_be_resolved_before_the_authority_is_notified(
    db_session: Session,
) -> None:
    incident = make_incident(
        db_session, is_serious=True, serious_category=SeriousIncidentCategory.OTHER
    )

    with pytest.raises(InvalidStatusTransitionError):
        ai_incident_service.update_incident(
            db_session, incident.id, AIIncidentUpdate(status="resolved"), actor_id=None
        )

    assert ai_incident_service.get_incident(db_session, incident.id).status == "open"


def test_a_serious_incident_resolves_once_the_notification_is_recorded(
    db_session: Session,
) -> None:
    incident = make_incident(
        db_session, is_serious=True, serious_category=SeriousIncidentCategory.OTHER
    )

    resolved = ai_incident_service.update_incident(
        db_session,
        incident.id,
        AIIncidentUpdate(status="resolved", authority_notified_on=date(2026, 3, 5)),
        actor_id=None,
    )

    assert resolved.status == AIIncidentStatus.RESOLVED
    assert resolved.resolved_at is not None


def test_reopening_clears_resolved_at(db_session: Session) -> None:
    incident = make_incident(db_session)
    ai_incident_service.update_incident(
        db_session, incident.id, AIIncidentUpdate(status="resolved"), actor_id=None
    )

    reopened = ai_incident_service.update_incident(
        db_session, incident.id, AIIncidentUpdate(status="investigating"), actor_id=None
    )

    assert reopened.resolved_at is None


def test_marking_not_serious_clears_the_category(db_session: Session) -> None:
    incident = make_incident(
        db_session, is_serious=True, serious_category=SeriousIncidentCategory.OTHER
    )

    updated = ai_incident_service.update_incident(
        db_session, incident.id, AIIncidentUpdate(is_serious=False), actor_id=None
    )

    assert updated.serious_category is None


def test_deleting_an_ai_system_unlinks_its_incidents_without_deleting_them(
    db_session: Session,
) -> None:
    row_id = make_ai_system(db_session)
    incident = make_incident(db_session, ai_system_row_id=row_id)

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    survivor = ai_incident_service.get_incident(db_session, incident.id)
    assert survivor.ai_system_row_id is None


def test_an_open_incident_can_be_deleted(db_session: Session) -> None:
    incident = make_incident(db_session)

    ai_incident_service.delete_incident(db_session, incident.id, actor_id=None)

    with pytest.raises(NotFoundError):
        ai_incident_service.get_incident(db_session, incident.id)


def test_an_incident_with_a_corrective_action_cannot_be_deleted(
    db_session: Session, make_user
) -> None:
    incident = make_incident(db_session)
    corrective_action_service.create_corrective_action(
        db_session,
        CorrectiveActionCreate(
            title="Remove age-correlated features",
            nonconformity_description=incident.description,
            source_type=ai_incident_service.ENTITY_TYPE,
            source_id=incident.id,
            assignee_id=make_user().id,
            due_date=date(2026, 4, 1),
        ),
        actor_id=None,
    )

    with pytest.raises(InvalidStatusTransitionError):
        ai_incident_service.delete_incident(db_session, incident.id, actor_id=None)
