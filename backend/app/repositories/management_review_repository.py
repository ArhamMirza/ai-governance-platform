from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.management_review_meeting import ManagementReviewMeeting
from app.models.management_review_settings import ManagementReviewSettings

# ---------- settings (singleton) ----------


def get_settings(db: Session) -> ManagementReviewSettings | None:
    """The singleton settings row, or None before one is stored."""
    return db.scalars(
        select(ManagementReviewSettings).order_by(ManagementReviewSettings.id)
    ).first()


def create_settings(db: Session, settings: ManagementReviewSettings) -> ManagementReviewSettings:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save_settings(db: Session, settings: ManagementReviewSettings) -> ManagementReviewSettings:
    db.commit()
    db.refresh(settings)
    return settings


# ---------- meetings ----------


def get_meeting(db: Session, meeting_id: int) -> ManagementReviewMeeting | None:
    return db.get(ManagementReviewMeeting, meeting_id)


def list_meetings(db: Session) -> list[ManagementReviewMeeting]:
    return list(
        db.scalars(select(ManagementReviewMeeting).order_by(ManagementReviewMeeting.meeting_date))
    )


def create_meeting(db: Session, meeting: ManagementReviewMeeting) -> ManagementReviewMeeting:
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


def save_meeting(db: Session, meeting: ManagementReviewMeeting) -> ManagementReviewMeeting:
    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, meeting: ManagementReviewMeeting) -> None:
    db.delete(meeting)
    db.commit()
