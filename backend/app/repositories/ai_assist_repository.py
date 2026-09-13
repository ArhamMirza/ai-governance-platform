from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_assist import AiAssistSettings, AiUsage


def get_settings_row(db: Session) -> AiAssistSettings | None:
    """The singleton settings row, or None before an admin has saved one."""
    return db.scalars(select(AiAssistSettings).order_by(AiAssistSettings.id)).first()


def create_settings(db: Session, settings: AiAssistSettings) -> AiAssistSettings:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save_settings(db: Session, settings: AiAssistSettings) -> AiAssistSettings:
    db.commit()
    db.refresh(settings)
    return settings


def record_usage(db: Session, usage: AiUsage) -> AiUsage:
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def tokens_used_today(db: Session, user_id: int | None) -> int:
    """Prompt + completion tokens this user has spent in the last 24 hours.

    A rolling window rather than a calendar day: it needs no timezone
    decision, and it can't be reset by waiting for midnight somewhere.
    """
    since = datetime.now(UTC) - timedelta(hours=24)
    total = db.scalar(
        select(
            func.coalesce(func.sum(AiUsage.prompt_tokens + AiUsage.completion_tokens), 0)
        ).where(AiUsage.user_id == user_id, AiUsage.created_at >= since)
    )
    return int(total or 0)
