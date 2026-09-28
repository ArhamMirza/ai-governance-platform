from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.schemas.management_review import (
    ManagementReviewMeetingCreate,
    ManagementReviewMeetingUpdate,
    ManagementReviewSettingsUpdate,
)
from app.services import management_review_service


def test_get_settings_returns_none_before_anything_is_configured(db_session: Session) -> None:
    assert management_review_service.get_settings(db_session) is None


def test_next_due_date_is_none_with_no_settings(db_session: Session) -> None:
    assert management_review_service.next_due_date(None, []) is None


def test_next_due_date_is_none_when_no_interval_is_configured(db_session: Session) -> None:
    settings = management_review_service.update_settings(
        db_session, ManagementReviewSettingsUpdate(interval_months=None), actor_id=None
    )

    assert management_review_service.next_due_date(settings, []) is None
    assert management_review_service.is_overdue(settings, []) is False


def test_next_due_date_is_start_date_before_any_meeting(db_session: Session) -> None:
    start = date.today() + timedelta(days=10)
    settings = management_review_service.update_settings(
        db_session,
        ManagementReviewSettingsUpdate(interval_months=12, start_date=start),
        actor_id=None,
    )

    assert management_review_service.next_due_date(settings, []) == start
    assert management_review_service.is_overdue(settings, []) is False


def test_next_due_date_advances_from_the_latest_meeting(db_session: Session) -> None:
    settings = management_review_service.update_settings(
        db_session,
        ManagementReviewSettingsUpdate(
            interval_months=12, start_date=date.today() - timedelta(days=400)
        ),
        actor_id=None,
    )
    meeting = management_review_service.create_meeting(
        db_session,
        ManagementReviewMeetingCreate(meeting_date=date.today()),
        actor_id=None,
    )

    due = management_review_service.next_due_date(settings, [meeting])

    assert due == date(date.today().year + 1, date.today().month, date.today().day)
    assert management_review_service.is_overdue(settings, [meeting]) is False


def test_is_overdue_when_start_date_has_passed_with_no_meetings(db_session: Session) -> None:
    settings = management_review_service.update_settings(
        db_session,
        ManagementReviewSettingsUpdate(
            interval_months=12, start_date=date.today() - timedelta(days=1)
        ),
        actor_id=None,
    )

    assert management_review_service.is_overdue(settings, []) is True


def test_create_and_update_meeting(db_session: Session) -> None:
    meeting = management_review_service.create_meeting(
        db_session,
        ManagementReviewMeetingCreate(
            meeting_date=date.today(),
            attendees="CAIGO, AI System Owner",
            decisions_and_actions="Approved a budget increase for monitoring tooling.",
        ),
        actor_id=None,
    )

    assert meeting.attendees == "CAIGO, AI System Owner"

    updated = management_review_service.update_meeting(
        db_session,
        meeting.id,
        ManagementReviewMeetingUpdate(context_changes="New EU AI Act guidance published."),
        actor_id=None,
    )

    assert updated.context_changes == "New EU AI Act guidance published."


def test_delete_meeting_removes_it(db_session: Session) -> None:
    meeting = management_review_service.create_meeting(
        db_session, ManagementReviewMeetingCreate(meeting_date=date.today()), actor_id=None
    )

    management_review_service.delete_meeting(db_session, meeting.id, actor_id=None)

    assert management_review_service.list_meetings(db_session) == []
