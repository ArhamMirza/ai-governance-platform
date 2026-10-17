from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ai_dlp import AIUsageEvent, AIUseSettings, DLPRule


def get_rule(db: Session, rule_id: int) -> DLPRule | None:
    return db.get(DLPRule, rule_id)


def list_rules(db: Session) -> list[DLPRule]:
    return list(db.scalars(select(DLPRule).order_by(DLPRule.name, DLPRule.id)))


def create_rule(db: Session, rule: DLPRule) -> DLPRule:
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def save_rule(db: Session, rule: DLPRule) -> DLPRule:
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule: DLPRule) -> None:
    db.delete(rule)
    db.commit()


def get_settings(db: Session) -> AIUseSettings | None:
    return db.scalars(select(AIUseSettings).limit(1)).first()


def create_settings(db: Session, settings: AIUseSettings) -> AIUseSettings:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save_settings(db: Session, settings: AIUseSettings) -> AIUseSettings:
    db.commit()
    db.refresh(settings)
    return settings


def find_event(
    db: Session,
    *,
    user_ref: str,
    day: date,
    domain: str,
    event_type: str,
    rule_id: int | None,
    action: str,
) -> AIUsageEvent | None:
    return db.scalars(
        select(AIUsageEvent).where(
            AIUsageEvent.user_ref == user_ref,
            AIUsageEvent.day == day,
            AIUsageEvent.domain == domain,
            AIUsageEvent.event_type == event_type,
            AIUsageEvent.rule_id == rule_id,
            AIUsageEvent.action == action,
        )
    ).first()


def add_event(db: Session, event: AIUsageEvent) -> None:
    db.add(event)


def commit(db: Session) -> None:
    db.commit()


def list_events_since(db: Session, since: date) -> list[AIUsageEvent]:
    return list(db.scalars(select(AIUsageEvent).where(AIUsageEvent.day >= since)))


def delete_events_before(db: Session, cutoff: date) -> int:
    result = db.execute(delete(AIUsageEvent).where(AIUsageEvent.day < cutoff))
    db.commit()
    return result.rowcount or 0
