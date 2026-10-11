"""The handler side of concerns: the register, triage, replies and settings.
Every route here is for the people handling concerns -- see
dependencies.require_concern_handler -- and nobody else."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import concern_tracking
from app.core.database import get_db
from app.dependencies import get_internal_user, require_concern_handler
from app.models.concern import Concern, ConcernSettings
from app.models.user import User, UserRole
from app.routers.corrective_actions import _to_read as _corrective_action_read
from app.schemas.concern import (
    ConcernAccess,
    ConcernLog,
    ConcernRead,
    ConcernSettingsRead,
    ConcernSettingsUpdate,
    ConcernStatusUpdate,
    ConcernUpdate,
    RaiseCorrectiveAction,
)
from app.schemas.corrective_action import CorrectiveActionRead
from app.services import concern_service, framework_service

router = APIRouter(prefix="/concerns", tags=["concerns"])


def _to_read(db: Session, concern: Concern, settings: ConcernSettings) -> ConcernRead:
    reporter = db.get(User, concern.reporter_id) if concern.reporter_id is not None else None
    return ConcernRead(
        id=concern.id,
        category=concern.category,
        description=concern.description,
        ai_system_row_id=concern.ai_system_row_id,
        system_note=concern.system_note,
        channel=concern.channel,
        received_on=concern.received_on,
        is_anonymous=concern.is_anonymous,
        reporter_id=concern.reporter_id,
        reporter_name=reporter.name if reporter is not None else None,
        reporter_note=concern.reporter_note,
        status=concern.status,
        handler_id=concern.handler_id,
        acknowledged_on=concern.acknowledged_on,
        closed_on=concern.closed_on,
        outcome=concern.outcome,
        internal_notes=concern.internal_notes,
        closure_note=concern.closure_note,
        reply_to_reporter=concern.reply_to_reporter,
        incident_id=concern.incident_id,
        acknowledge_by=concern_tracking.acknowledge_by(
            concern.received_on, settings.acknowledge_within_days
        ),
        awaiting_triage=concern_service.is_awaiting_triage(concern, settings, None),
    )


def _settings_read(db: Session, settings: ConcernSettings) -> ConcernSettingsRead:
    return ConcernSettingsRead(
        id=settings.id,
        process_description=settings.process_description,
        acknowledge_within_days=settings.acknowledge_within_days,
        framework_tags=framework_service.get_tags(
            db, concern_service.SETTINGS_ENTITY_TYPE, settings.id
        ),
    )


# Who sees the Concerns page in the navigation. Open to every internal user --
# it only says whether *they* can handle concerns, never anything about any.
@router.get("/access", response_model=ConcernAccess)
def access(user: User = Depends(get_internal_user)) -> ConcernAccess:
    return ConcernAccess(can_handle=user.role == UserRole.ADMIN)


# Declared before /{concern_id}, so "settings" isn't taken for an id.
@router.get("/settings", response_model=ConcernSettingsRead)
def get_settings(
    db: Session = Depends(get_db), _handler: User = Depends(require_concern_handler)
) -> ConcernSettingsRead:
    return _settings_read(db, concern_service.get_settings(db))


@router.put("/settings", response_model=ConcernSettingsRead)
def update_settings(
    data: ConcernSettingsUpdate,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> ConcernSettingsRead:
    return _settings_read(db, concern_service.update_settings(db, data, handler.id))


@router.get("", response_model=list[ConcernRead])
def list_concerns(
    db: Session = Depends(get_db), _handler: User = Depends(require_concern_handler)
) -> list[ConcernRead]:
    settings = concern_service.settings_or_default(db)
    return [_to_read(db, concern, settings) for concern in concern_service.list_concerns(db)]


@router.post("", response_model=ConcernRead, status_code=201)
def log_concern(
    data: ConcernLog,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> ConcernRead:
    concern = concern_service.log_concern(db, data, handler.id)
    return _to_read(db, concern, concern_service.settings_or_default(db))


@router.get("/{concern_id}", response_model=ConcernRead)
def get_concern(
    concern_id: int,
    db: Session = Depends(get_db),
    _handler: User = Depends(require_concern_handler),
) -> ConcernRead:
    return _to_read(
        db, concern_service.get_concern(db, concern_id), concern_service.settings_or_default(db)
    )


@router.put("/{concern_id}", response_model=ConcernRead)
def update_concern(
    concern_id: int,
    data: ConcernUpdate,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> ConcernRead:
    concern = concern_service.update_concern(db, concern_id, data, handler.id)
    return _to_read(db, concern, concern_service.settings_or_default(db))


@router.post("/{concern_id}/status", response_model=ConcernRead)
def change_status(
    concern_id: int,
    data: ConcernStatusUpdate,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> ConcernRead:
    concern = concern_service.change_status(db, concern_id, data, handler.id)
    return _to_read(db, concern, concern_service.settings_or_default(db))


@router.post("/{concern_id}/raise-incident", response_model=ConcernRead)
def raise_incident(
    concern_id: int,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> ConcernRead:
    concern = concern_service.raise_incident(db, concern_id, handler.id)
    return _to_read(db, concern, concern_service.settings_or_default(db))


@router.get("/{concern_id}/corrective-actions", response_model=list[CorrectiveActionRead])
def list_corrective_actions(
    concern_id: int,
    db: Session = Depends(get_db),
    _handler: User = Depends(require_concern_handler),
) -> list[CorrectiveActionRead]:
    return [
        _corrective_action_read(db, action)
        for action in concern_service.list_corrective_actions(db, concern_id)
    ]


@router.post(
    "/{concern_id}/corrective-actions", response_model=CorrectiveActionRead, status_code=201
)
def raise_corrective_action(
    concern_id: int,
    data: RaiseCorrectiveAction,
    db: Session = Depends(get_db),
    handler: User = Depends(require_concern_handler),
) -> CorrectiveActionRead:
    return _corrective_action_read(
        db, concern_service.raise_corrective_action(db, concern_id, data, handler.id)
    )
