from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.corrective_action import CorrectiveActionStatus
from app.repositories import audit_log_repository
from app.services import audit_service


def test_log_stores_dates_datetimes_and_enums_as_json(db_session: Session) -> None:
    """Callers pass model_dump() change sets straight through; the JSON
    diff column can't hold date/datetime/enum objects as they are."""
    audit_service.log(
        db_session,
        "CorrectiveAction",
        1,
        "updated",
        None,
        {
            "due_date": date(2026, 4, 1),
            "closed_at": datetime(2026, 4, 1, 9, 30, tzinfo=UTC),
            "status": CorrectiveActionStatus.IN_PROGRESS,
            "title": "unchanged",
        },
    )

    entry = audit_log_repository.list_for_entity(db_session, "CorrectiveAction", 1)[-1]
    assert entry.diff == {
        "due_date": "2026-04-01",
        "closed_at": "2026-04-01T09:30:00+00:00",
        "status": "in_progress",
        "title": "unchanged",
    }


def test_log_without_a_diff_stores_none(db_session: Session) -> None:
    entry = audit_service.log(db_session, "Policy", 1, "deleted", None)

    assert entry.diff is None
