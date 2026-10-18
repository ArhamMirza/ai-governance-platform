from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.password_history import PasswordHistory


def recent_hashes(db: Session, user_id: int) -> list[str]:
    return list(
        db.scalars(
            select(PasswordHistory.password_hash)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.id.desc())
        )
    )


def remember(db: Session, user_id: int, password_hash: str, keep: int) -> None:
    """Adds a retired hash and drops all but the newest `keep`. Committed by
    the caller, together with the change that retired it."""
    db.add(PasswordHistory(user_id=user_id, password_hash=password_hash))
    db.flush()
    newest = list(
        db.scalars(
            select(PasswordHistory.id)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.id.desc())
            .limit(keep)
        )
    )
    db.execute(
        delete(PasswordHistory).where(
            PasswordHistory.user_id == user_id, PasswordHistory.id.not_in(newest)
        )
    )
