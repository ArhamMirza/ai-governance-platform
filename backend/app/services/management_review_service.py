"""Management review -- ISO/IEC 42001 Clause 9.3.

Settings and meetings together, the same way internal_audit_service.py
covers AuditProgram/InternalAudit/AuditFinding in one file. Unlike Clause
9.2 (many possible audit programs), Clause 9.3 is inherently singular --
one organization has one management review process -- so the schedule is
a singleton (ManagementReviewSettings), mirroring risk_criteria_service's
get-or-defaults pattern, not a per-program record.

next_due_date/is_overdue reuse app.core.audit_schedule directly rather
than reimplementing the same interval math a second time -- the rule is
identical to AuditProgram's: due on start_date until the first review
happens, then interval_months on from the latest one's date.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import audit_schedule
from app.core.exceptions import NotFoundError
from app.models.management_review_meeting import ManagementReviewMeeting
from app.models.management_review_settings import ManagementReviewSettings
from app.repositories import management_review_repository
from app.schemas.management_review import (
    ManagementReviewMeetingCreate,
    ManagementReviewMeetingUpdate,
    ManagementReviewSettingsUpdate,
)
from app.services import audit_service, evidence_service, framework_service

MEETING_ENTITY_TYPE = "ManagementReviewMeeting"
SETTINGS_ENTITY_TYPE = "ManagementReviewSettings"
# The singleton settings row's audit/tag entity id -- there is only ever one.
SETTINGS_ENTITY_ID = 1


# ---------- schedule ----------


def next_due_date(
    settings: ManagementReviewSettings | None, meetings: list[ManagementReviewMeeting]
) -> date | None:
    """None once no interval is configured -- reviews are logged as they
    happen, with nothing to be due. Otherwise due on start_date until the
    first meeting is recorded, then interval_months on from the latest
    one's meeting_date."""
    if settings is None or settings.interval_months is None:
        return None
    if not meetings:
        return settings.start_date
    latest = max(meeting.meeting_date for meeting in meetings)
    return audit_schedule.next_audit_date(latest, settings.interval_months)


def is_overdue(
    settings: ManagementReviewSettings | None,
    meetings: list[ManagementReviewMeeting],
    today: date | None = None,
) -> bool:
    reference = today if today is not None else datetime.now(UTC).date()
    return audit_schedule.is_audit_overdue(next_due_date(settings, meetings), reference)


# ---------- settings ----------


def get_settings(db: Session) -> ManagementReviewSettings | None:
    return management_review_repository.get_settings(db)


def update_settings(
    db: Session, data: ManagementReviewSettingsUpdate, actor_id: int | None
) -> ManagementReviewSettings:
    settings = management_review_repository.get_settings(db)
    if settings is None:
        settings = management_review_repository.create_settings(
            db,
            ManagementReviewSettings(
                interval_months=data.interval_months, start_date=data.start_date
            ),
        )
    else:
        settings.interval_months = data.interval_months
        settings.start_date = data.start_date
        settings = management_review_repository.save_settings(db, settings)

    audit_service.log(
        db,
        SETTINGS_ENTITY_TYPE,
        SETTINGS_ENTITY_ID,
        "updated",
        actor_id,
        {"interval_months": data.interval_months, "start_date": str(data.start_date)},
    )
    return settings


# ---------- meetings ----------


def _get_meeting_or_raise(db: Session, meeting_id: int) -> ManagementReviewMeeting:
    meeting = management_review_repository.get_meeting(db, meeting_id)
    if meeting is None:
        raise NotFoundError("ManagementReviewMeeting", meeting_id)
    return meeting


def list_meetings(db: Session) -> list[ManagementReviewMeeting]:
    return management_review_repository.list_meetings(db)


def get_meeting(db: Session, meeting_id: int) -> ManagementReviewMeeting:
    return _get_meeting_or_raise(db, meeting_id)


def create_meeting(
    db: Session, data: ManagementReviewMeetingCreate, actor_id: int | None
) -> ManagementReviewMeeting:
    meeting = ManagementReviewMeeting(**data.model_dump())
    meeting = management_review_repository.create_meeting(db, meeting)
    audit_service.log(
        db,
        MEETING_ENTITY_TYPE,
        meeting.id,
        "created",
        actor_id,
        {"meeting_date": str(meeting.meeting_date)},
    )
    return meeting


def update_meeting(
    db: Session, meeting_id: int, data: ManagementReviewMeetingUpdate, actor_id: int | None
) -> ManagementReviewMeeting:
    meeting = _get_meeting_or_raise(db, meeting_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(meeting, field, value)
    meeting = management_review_repository.save_meeting(db, meeting)
    audit_service.log(db, MEETING_ENTITY_TYPE, meeting.id, "updated", actor_id, changes)
    return meeting


def delete_meeting(db: Session, meeting_id: int, actor_id: int | None) -> None:
    meeting = _get_meeting_or_raise(db, meeting_id)
    management_review_repository.delete_meeting(db, meeting)
    evidence_service.delete_all_for_entity(db, MEETING_ENTITY_TYPE, meeting_id)
    framework_service.delete_tags(db, MEETING_ENTITY_TYPE, meeting_id)
    audit_service.log(db, MEETING_ENTITY_TYPE, meeting_id, "deleted", actor_id)
