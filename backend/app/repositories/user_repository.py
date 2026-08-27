from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
