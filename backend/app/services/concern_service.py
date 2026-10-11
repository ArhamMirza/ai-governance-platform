"""Reporting of concerns -- ISO/IEC 42001 A.3.3.

Two audiences, kept apart:

- **Reporters** (employees, who have no other access to the platform) submit
  a concern -- named or anonymous -- and follow it through the employee home
  or, for an anonymous one, a tracking code. They only ever see their own.
- **Handlers** (admins and Chief AI Governance Officer role holders -- see
  dependencies.require_concern_handler) triage, reply, resolve and raise
  incidents. Nobody else can read a concern, because one can name colleagues
  or describe misconduct.

What an anonymous concern does and doesn't keep is the point of this module:
no reporter, no audit entry for the submission, no timestamps -- see Concern.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import concern_tracking
from app.core.attempt_limiter import AttemptLimiter
from app.core.exceptions import (
    InvalidStatusTransitionError,
    NotFoundError,
    ValidationError,
)
from app.models.concern import (
    Concern,
    ConcernChannel,
    ConcernSettings,
    ConcernStatus,
)
from app.models.user import User
from app.repositories import (
    ai_system_lifecycle_repository,
    concern_repository,
    sheet_repository,
)
from app.schemas.ai_incident import AIIncidentCreate
from app.schemas.concern import (
    ConcernLog,
    ConcernSettingsUpdate,
    ConcernStatusUpdate,
    ConcernSubmit,
    ConcernUpdate,
    RaiseCorrectiveAction,
)
from app.schemas.corrective_action import CorrectiveActionCreate
from app.services import (
    ai_incident_service,
    ai_system_inventory_service,
    audit_service,
    corrective_action_service,
)

ENTITY_TYPE = "Concern"
SETTINGS_ENTITY_TYPE = "ConcernSettings"
DEFAULT_ACKNOWLEDGE_DAYS = 7

# Five wrong codes in a quarter of an hour, per person asking.
_lookup_limiter = AttemptLimiter(
    max_failures=5,
    window=timedelta(minutes=15),
    message="Too many tracking codes tried. Wait fifteen minutes and try again.",
)


def reset_lookup_limits() -> None:
    """For tests: the limiter is process-wide state."""
    _lookup_limiter.reset()


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


# ---------- settings ----------


def get_settings(db: Session) -> ConcernSettings:
    """The one settings row, provisioned (with its defaults) on first use."""
    settings = concern_repository.get_settings(db)
    if settings is None:
        settings = concern_repository.create_settings(
            db, ConcernSettings(acknowledge_within_days=DEFAULT_ACKNOWLEDGE_DAYS)
        )
    return settings


def settings_or_default(db: Session) -> ConcernSettings:
    """The settings if they've been saved, else the defaults -- without writing
    a row, for the dashboard and compliance reads."""
    return concern_repository.get_settings(db) or ConcernSettings(
        acknowledge_within_days=DEFAULT_ACKNOWLEDGE_DAYS
    )


def update_settings(
    db: Session, data: ConcernSettingsUpdate, actor_id: int | None
) -> ConcernSettings:
    settings = get_settings(db)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("acknowledge_within_days", 1) is None:
        raise ValidationError("Say how many days a concern may wait to be acknowledged.")
    for field, value in changes.items():
        setattr(settings, field, value)
    settings = concern_repository.save_settings(db, settings)
    audit_service.log(db, SETTINGS_ENTITY_TYPE, settings.id, "updated", actor_id, changes)
    return settings


# ---------- shared checks ----------


def _get_or_raise(db: Session, concern_id: int) -> Concern:
    concern = concern_repository.get(db, concern_id)
    if concern is None:
        raise NotFoundError("Concern", concern_id)
    return concern


def _validate_ai_system(db: Session, row_id: int | None, *, in_service_only: bool) -> None:
    if row_id is None:
        return
    inventory = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, row_id)
    if row is None or row.sheet_id != inventory.id:
        raise NotFoundError("AISystemRow", row_id)
    if in_service_only:
        lifecycle = ai_system_lifecycle_repository.get_for_ai_system(db, row_id)
        if lifecycle is not None and lifecycle.archived_at is not None:
            raise NotFoundError("AISystemRow", row_id)


def is_awaiting_triage(concern: Concern, settings: ConcernSettings, today: date | None) -> bool:
    return concern_tracking.awaiting_triage(
        concern.status, concern.received_on, settings.acknowledge_within_days, _today(today)
    )


# ---------- reporters (employees) ----------


def in_service_ai_systems(db: Session) -> list[tuple[int, str]]:
    """Id and name of each AI system in service -- all an employee needs to
    say which one a concern is about. The inventory listing already leaves
    out archived systems."""
    systems = [
        (row.id, str(row.data.get("name") or f"AI System #{row.id}"))
        for row in ai_system_inventory_service.list_rows(db)
    ]
    return sorted(systems, key=lambda system: system[1].lower())


def submit(
    db: Session, reporter: User, data: ConcernSubmit, today: date | None = None
) -> tuple[Concern, str]:
    """Records a concern from an employee. Returns it with its tracking code,
    which can be shown only now -- only the code's hash is kept.

    Anonymous: no reporter id, and no audit entry (whose actor and timestamp
    would tie it to this person's session). Named: the reporter is recorded
    and the receipt audit-logged like any other record."""
    _validate_ai_system(db, data.ai_system_row_id, in_service_only=True)
    code = concern_tracking.new_tracking_code()
    concern = concern_repository.create(
        db,
        Concern(
            category=data.category,
            description=data.description.strip(),
            ai_system_row_id=data.ai_system_row_id,
            system_note=(data.system_note or "").strip() or None,
            channel=ConcernChannel.EMPLOYEE_PORTAL,
            received_on=_today(today),
            is_anonymous=data.anonymous,
            reporter_id=None if data.anonymous else reporter.id,
            tracking_code_hash=concern_tracking.hash_code(code),
            status=ConcernStatus.RECEIVED,
        ),
    )
    if not data.anonymous:
        audit_service.log(db, ENTITY_TYPE, concern.id, "received", reporter.id)
    return concern, concern_tracking.format_code(code)


def list_mine(db: Session, reporter: User) -> list[Concern]:
    """The concerns this person raised under their own name. Anonymous ones
    aren't listed -- nothing links them to anyone; they come back by code."""
    return concern_repository.list_for_reporter(db, reporter.id)


def lookup(db: Session, asker: User, tracking_code: str) -> Concern:
    """The concern a tracking code belongs to. A wrong code counts against the
    person asking; too many in a short while and they're told to wait."""
    key = str(asker.id)
    _lookup_limiter.check(key)
    concern = None
    if concern_tracking.looks_like_a_code(tracking_code):
        concern = concern_repository.get_by_code_hash(db, concern_tracking.hash_code(tracking_code))
    if concern is None:
        _lookup_limiter.record_failure(key)
        # One answer for a malformed code and for one that matches nothing.
        raise NotFoundError("Concern", 0)
    return concern


# ---------- handlers ----------


def list_concerns(db: Session) -> list[Concern]:
    return concern_repository.list_all(db)


def get_concern(db: Session, concern_id: int) -> Concern:
    return _get_or_raise(db, concern_id)


def log_concern(
    db: Session, data: ConcernLog, handler_id: int | None, today: date | None = None
) -> Concern:
    """A handler records a concern raised by phone, email or in person."""
    if data.channel == ConcernChannel.EMPLOYEE_PORTAL:
        raise ValidationError(
            "Concerns raised through the employee home are recorded by the person raising them."
        )
    received_on = data.received_on or _today(today)
    if received_on > _today(today):
        raise ValidationError("A concern can't be dated in the future.")
    _validate_ai_system(db, data.ai_system_row_id, in_service_only=False)
    concern = concern_repository.create(
        db,
        Concern(
            category=data.category,
            description=data.description.strip(),
            ai_system_row_id=data.ai_system_row_id,
            system_note=(data.system_note or "").strip() or None,
            channel=data.channel,
            received_on=received_on,
            is_anonymous=data.anonymous,
            reporter_note=None if data.anonymous else data.reporter_note,
            status=ConcernStatus.RECEIVED,
        ),
    )
    audit_service.log(
        db, ENTITY_TYPE, concern.id, "logged", handler_id, {"channel": data.channel.value}
    )
    return concern


def update_concern(
    db: Session, concern_id: int, data: ConcernUpdate, handler_id: int | None
) -> Concern:
    concern = _get_or_raise(db, concern_id)
    changes = data.model_dump(exclude_unset=True)
    if "ai_system_row_id" in changes:
        _validate_ai_system(db, changes["ai_system_row_id"], in_service_only=False)
    for field, value in changes.items():
        setattr(concern, field, value)
    concern = concern_repository.save(db, concern)
    # The text of a reply or note isn't copied into the audit log: it can
    # name people. What changed is recorded, not what was said.
    audit_service.log(
        db, ENTITY_TYPE, concern.id, "updated", handler_id, {"fields": sorted(changes)}
    )
    return concern


def change_status(
    db: Session,
    concern_id: int,
    data: ConcernStatusUpdate,
    handler_id: int | None,
    today: date | None = None,
) -> Concern:
    concern = _get_or_raise(db, concern_id)
    reference = _today(today)
    closed = concern.status in (ConcernStatus.RESOLVED, ConcernStatus.NOT_ACTIONED)

    if data.action == "acknowledge":
        if concern.status != ConcernStatus.RECEIVED:
            raise InvalidStatusTransitionError(
                f"Concern {concern_id} is {concern.status}; only a new one is acknowledged."
            )
        concern.status = ConcernStatus.UNDER_REVIEW
        concern.acknowledged_on = reference
        if concern.handler_id is None:
            concern.handler_id = handler_id
    elif data.action in ("resolve", "dismiss"):
        if closed:
            raise InvalidStatusTransitionError(f"Concern {concern_id} is already closed.")
        if data.action == "resolve" and data.outcome is None:
            raise ValidationError("Say how it turned out before resolving a concern.")
        if data.action == "dismiss" and not (data.note or "").strip():
            raise ValidationError("Say why it isn't being taken further.")
        if concern.acknowledged_on is None:
            concern.acknowledged_on = reference
        if concern.handler_id is None:
            concern.handler_id = handler_id
        concern.closed_on = reference
        if data.action == "resolve":
            concern.status = ConcernStatus.RESOLVED
            concern.outcome = data.outcome
            concern.closure_note = (data.note or "").strip() or None
        else:
            concern.status = ConcernStatus.NOT_ACTIONED
            concern.outcome = None
            concern.closure_note = (data.note or "").strip()
    else:  # reopen
        if not closed:
            raise InvalidStatusTransitionError(f"Concern {concern_id} is still open.")
        concern.status = ConcernStatus.UNDER_REVIEW
        concern.closed_on = None
        concern.outcome = None
        concern.closure_note = None

    concern = concern_repository.save(db, concern)
    audit_service.log(
        db, ENTITY_TYPE, concern.id, f"status_{data.action}", handler_id, {"status": concern.status}
    )
    return concern


def raise_incident(
    db: Session, concern_id: int, handler_id: int | None, today: date | None = None
) -> Concern:
    """Opens an AI incident from the concern, so what it turned up is tracked
    (and, if serious, reported) like any other. The incident carries the
    concern's description and system -- never who raised it."""
    concern = _get_or_raise(db, concern_id)
    if concern.incident_id is not None:
        raise InvalidStatusTransitionError(
            f"An incident (#{concern.incident_id}) has already been raised from this concern."
        )
    incident = ai_incident_service.create_incident(
        db,
        AIIncidentCreate(
            title=f"Raised from a concern: {concern.description[:80].strip()}",
            description=concern.description,
            ai_system_row_id=concern.ai_system_row_id,
            detected_on=_today(today),
            owner_id=handler_id,
        ),
        handler_id,
    )
    concern.incident_id = incident.id
    if concern.acknowledged_on is None:
        concern.acknowledged_on = _today(today)
        concern.status = ConcernStatus.UNDER_REVIEW
    concern = concern_repository.save(db, concern)
    audit_service.log(
        db, ENTITY_TYPE, concern.id, "incident_raised", handler_id, {"incident_id": incident.id}
    )
    return concern


def raise_corrective_action(
    db: Session, concern_id: int, data: RaiseCorrectiveAction, handler_id: int | None
):
    """A corrective action sourced from this concern, listed on it."""
    concern = _get_or_raise(db, concern_id)
    action = corrective_action_service.create_corrective_action(
        db,
        CorrectiveActionCreate(
            title=data.title,
            nonconformity_description=concern.description,
            action_description=data.action_description,
            source_type=ENTITY_TYPE,
            source_id=concern.id,
            assignee_id=data.assignee_id,
            due_date=data.due_date,
        ),
        handler_id,
    )
    audit_service.log(
        db,
        ENTITY_TYPE,
        concern.id,
        "corrective_action_raised",
        handler_id,
        {"corrective_action_id": action.id},
    )
    return action


def list_corrective_actions(db: Session, concern_id: int):
    _get_or_raise(db, concern_id)
    return corrective_action_service.list_for_source(db, ENTITY_TYPE, concern_id)


def unlink_ai_system(db: Session, ai_system_row_id: int, handler_id: int | None) -> None:
    """A concern about an AI system that's later deleted keeps what was said;
    only the link goes, and what the system was called is kept in the note."""
    for concern in concern_repository.list_for_ai_system(db, ai_system_row_id):
        row = sheet_repository.get_row(db, ai_system_row_id)
        name = str(row.data.get("name")) if row is not None and row.data.get("name") else None
        concern.ai_system_row_id = None
        if name and not concern.system_note:
            concern.system_note = f"{name} (since deleted)"
        concern_repository.save(db, concern)
        audit_service.log(
            db,
            ENTITY_TYPE,
            concern.id,
            "ai_system_unlinked",
            handler_id,
            {"ai_system_row_id": ai_system_row_id},
        )


# ---------- standing, for the dashboard and compliance ----------


@dataclass(frozen=True)
class Standing:
    open_count: int
    awaiting_triage_count: int


def standing(db: Session, today: date | None = None) -> Standing:
    settings = settings_or_default(db)
    concerns = concern_repository.list_all(db)
    return Standing(
        open_count=sum(
            1 for c in concerns if c.status in (ConcernStatus.RECEIVED, ConcernStatus.UNDER_REVIEW)
        ),
        awaiting_triage_count=sum(1 for c in concerns if is_awaiting_triage(c, settings, today)),
    )
