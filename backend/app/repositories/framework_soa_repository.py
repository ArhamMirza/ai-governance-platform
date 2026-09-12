from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.concurrency import create_or_get
from app.models.framework_soa_entry import FrameworkSoaEntry


def list_all(db: Session) -> list[FrameworkSoaEntry]:
    return list(db.scalars(select(FrameworkSoaEntry)))


def get_by_control_id(db: Session, control_id: int) -> FrameworkSoaEntry | None:
    return db.scalar(
        select(FrameworkSoaEntry).where(FrameworkSoaEntry.framework_control_id == control_id)
    )


def upsert(
    db: Session,
    control_id: int,
    applicability: str,
    justification: str | None,
    actor_id: int | None,
) -> FrameworkSoaEntry:
    entry = get_by_control_id(db, control_id)
    if entry is None:
        # A control's entry is seeded by migration, so this only runs for one
        # added since -- where two simultaneous decisions would each insert.
        entry = create_or_get(
            db,
            lambda: FrameworkSoaEntry(framework_control_id=control_id),
            lambda: get_by_control_id(db, control_id),
        )
    entry.applicability = applicability
    entry.justification = justification
    entry.updated_by = actor_id
    entry.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(entry)
    return entry
