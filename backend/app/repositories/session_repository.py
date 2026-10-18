from datetime import datetime

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session


def create(db: DbSession, session: Session) -> Session:
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_by_token_hash(db: DbSession, token_hash: str) -> Session | None:
    return db.scalar(select(Session).where(Session.token_hash == token_hash))


def delete(db: DbSession, session: Session) -> None:
    db.delete(session)
    db.commit()


def delete_by_token_hash(db: DbSession, token_hash: str) -> None:
    session = get_by_token_hash(db, token_hash)
    if session is not None:
        delete(db, session)


def delete_for_user(db: DbSession, user_id: int, keep_token_hash: str | None = None) -> int:
    """Ends every session of a user, optionally sparing the one making the
    request. Returns how many were ended."""
    query = sql_delete(Session).where(Session.user_id == user_id)
    if keep_token_hash is not None:
        query = query.where(Session.token_hash != keep_token_hash)
    result = db.execute(query)
    db.commit()
    return result.rowcount or 0


def delete_expired(db: DbSession, now: datetime) -> None:
    db.execute(sql_delete(Session).where(Session.expires_at < now))
    db.commit()
