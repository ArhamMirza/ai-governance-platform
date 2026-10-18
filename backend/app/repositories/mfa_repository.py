from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.mfa import MFARecoveryCode, SecuritySettings, UserMFA


def get(db: Session, user_id: int) -> UserMFA | None:
    return db.scalar(select(UserMFA).where(UserMFA.user_id == user_id))


def save(db: Session, mfa: UserMFA) -> UserMFA:
    db.add(mfa)
    db.commit()
    db.refresh(mfa)
    return mfa


def advance_step(db: Session, mfa_id: int, step: int) -> bool:
    """Records that a code from this step was used -- only if no code from this
    step or a later one has been. One atomic statement, so two requests
    presenting the same code at the same moment can't both succeed."""
    result = db.execute(
        update(UserMFA)
        .where(UserMFA.id == mfa_id)
        .where((UserMFA.last_used_step.is_(None)) | (UserMFA.last_used_step < step))
        .values(last_used_step=step)
    )
    db.commit()
    return result.rowcount == 1


def replace_recovery_codes(db: Session, user_id: int, hashes: list[str]) -> None:
    db.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
    db.add_all(MFARecoveryCode(user_id=user_id, code_hash=h) for h in hashes)
    db.commit()


def use_recovery_code(db: Session, user_id: int, code_hash: str) -> bool:
    """Spends a matching unused code. One atomic statement, like advance_step:
    two requests presenting the same code at once cannot both succeed."""
    result = db.execute(
        update(MFARecoveryCode)
        .where(
            MFARecoveryCode.user_id == user_id,
            MFARecoveryCode.code_hash == code_hash,
            MFARecoveryCode.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )
    db.commit()
    return result.rowcount == 1


def unused_recovery_codes(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(MFARecoveryCode)
            .where(MFARecoveryCode.user_id == user_id, MFARecoveryCode.used_at.is_(None))
        )
        or 0
    )


def delete_for_user(db: Session, user_id: int) -> None:
    db.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
    db.execute(delete(UserMFA).where(UserMFA.user_id == user_id))
    db.commit()
    db.expire_all()


# ---------- the organization-wide setting ----------


def get_settings(db: Session) -> SecuritySettings | None:
    return db.scalar(select(SecuritySettings).limit(1))


def save_settings(db: Session, settings: SecuritySettings) -> SecuritySettings:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def count_admins_without_mfa(db: Session) -> int:
    from app.models.user import User, UserRole

    confirmed = select(UserMFA.user_id).where(UserMFA.confirmed.is_(True))
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .where(User.id.not_in(confirmed))
        )
        or 0
    )
