import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.framework_control import FrameworkControl

_CODE_SEGMENT = re.compile(r"(\d+)")


def _natural_code_key(control: FrameworkControl) -> tuple:
    """Sorts "4.1", "10.2", "A.6.1.2" in the order a human reads them --
    plain string ordering puts "10.1" before "4.1" since "1" < "4"."""
    parts = _CODE_SEGMENT.split(control.code)
    return (control.framework, tuple(int(p) if p.isdigit() else p for p in parts))


def list_all(
    db: Session, framework: str | None = None, category: str | None = None
) -> list[FrameworkControl]:
    query = select(FrameworkControl)
    if framework is not None:
        query = query.where(FrameworkControl.framework == framework)
    if category is not None:
        query = query.where(FrameworkControl.category == category)
    return sorted(db.scalars(query), key=_natural_code_key)


def list_by_ids(db: Session, control_ids: list[int]) -> list[FrameworkControl]:
    if not control_ids:
        return []
    return list(
        db.scalars(select(FrameworkControl).where(FrameworkControl.id.in_(control_ids)))
    )


def get_by_id(db: Session, control_id: int) -> FrameworkControl | None:
    return db.get(FrameworkControl, control_id)
