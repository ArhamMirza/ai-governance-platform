from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.management_review_meeting import ManagementReviewMeeting
from app.schemas.management_review import (
    ManagementReviewMeetingCreate,
    ManagementReviewMeetingRead,
    ManagementReviewMeetingUpdate,
    ManagementReviewSettingsRead,
    ManagementReviewSettingsUpdate,
)
from app.services import framework_service, management_review_service

router = APIRouter(prefix="/management-review", tags=["management-review"])


def _settings_to_read(db: Session) -> ManagementReviewSettingsRead:
    settings = management_review_service.get_settings(db)
    meetings = management_review_service.list_meetings(db)
    framework_tags = framework_service.get_tags(
        db,
        management_review_service.SETTINGS_ENTITY_TYPE,
        management_review_service.SETTINGS_ENTITY_ID,
    )
    return ManagementReviewSettingsRead(
        interval_months=settings.interval_months if settings else None,
        start_date=settings.start_date if settings else None,
        next_due_date=management_review_service.next_due_date(settings, meetings),
        overdue=management_review_service.is_overdue(settings, meetings, datetime.now(UTC).date()),
        framework_tags=framework_tags,
        updated_at=settings.updated_at if settings else None,
    )


def _meeting_to_read(db: Session, meeting: ManagementReviewMeeting) -> ManagementReviewMeetingRead:
    framework_tags = framework_service.get_tags(
        db, management_review_service.MEETING_ENTITY_TYPE, meeting.id
    )
    return ManagementReviewMeetingRead(
        id=meeting.id,
        meeting_date=meeting.meeting_date,
        chaired_by=meeting.chaired_by,
        attendees=meeting.attendees,
        previous_actions_status=meeting.previous_actions_status,
        context_changes=meeting.context_changes,
        performance_summary=meeting.performance_summary,
        stakeholder_feedback=meeting.stakeholder_feedback,
        resource_adequacy=meeting.resource_adequacy,
        improvement_opportunities=meeting.improvement_opportunities,
        decisions_and_actions=meeting.decisions_and_actions,
        framework_tags=framework_tags,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("/settings", response_model=ManagementReviewSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> ManagementReviewSettingsRead:
    return _settings_to_read(db)


@router.put("/settings", response_model=ManagementReviewSettingsRead)
def update_settings(
    data: ManagementReviewSettingsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ManagementReviewSettingsRead:
    management_review_service.update_settings(db, data, actor_id)
    return _settings_to_read(db)


@router.get("/meetings", response_model=list[ManagementReviewMeetingRead])
def list_meetings(db: Session = Depends(get_db)) -> list[ManagementReviewMeetingRead]:
    return [_meeting_to_read(db, m) for m in management_review_service.list_meetings(db)]


@router.post("/meetings", response_model=ManagementReviewMeetingRead, status_code=201)
def create_meeting(
    data: ManagementReviewMeetingCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ManagementReviewMeetingRead:
    meeting = management_review_service.create_meeting(db, data, actor_id)
    return _meeting_to_read(db, meeting)


@router.get("/meetings/{meeting_id}", response_model=ManagementReviewMeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> ManagementReviewMeetingRead:
    return _meeting_to_read(db, management_review_service.get_meeting(db, meeting_id))


@router.put("/meetings/{meeting_id}", response_model=ManagementReviewMeetingRead)
def update_meeting(
    meeting_id: int,
    data: ManagementReviewMeetingUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ManagementReviewMeetingRead:
    meeting = management_review_service.update_meeting(db, meeting_id, data, actor_id)
    return _meeting_to_read(db, meeting)


@router.delete("/meetings/{meeting_id}", status_code=204)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    management_review_service.delete_meeting(db, meeting_id, actor_id)
