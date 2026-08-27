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
