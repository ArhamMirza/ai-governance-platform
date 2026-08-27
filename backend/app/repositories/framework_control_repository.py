from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.framework_control import FrameworkControl


def list_all(db: Session, framework: str | None = None) -> list[FrameworkControl]:
    query = select(FrameworkControl)
    if framework is not None:
        query = query.where(FrameworkControl.framework == framework)
    return list(
        db.scalars(query.order_by(FrameworkControl.framework, FrameworkControl.code))
    )


def list_by_ids(db: Session, control_ids: list[int]) -> list[FrameworkControl]:
    if not control_ids:
        return []
    return list(
        db.scalars(select(FrameworkControl).where(FrameworkControl.id.in_(control_ids)))
    )
