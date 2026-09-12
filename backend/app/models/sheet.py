from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Sheets the app treats as the one and only sheet of their kind -- both are
# reached through a get_or_create that would otherwise let two simultaneous
# first requests each provision their own. Deliberately not every entity
# type: a risk assessment gets a fresh "Risk Items" sheet per assessment, so
# a blanket unique constraint on entity_type would break them outright.
SINGLETON_ENTITY_TYPES = ("AISystemInventory", "DataInventory")

_SINGLETON_PREDICATE = text(
    "entity_type IN ('{}')".format("', '".join(SINGLETON_ENTITY_TYPES))
)


class Sheet(Base):
    __tablename__ = "sheets"
    __table_args__ = (
        Index(
            "uq_sheets_singleton_entity_type",
            "entity_type",
            unique=True,
            sqlite_where=_SINGLETON_PREDICATE,
            postgresql_where=_SINGLETON_PREDICATE,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    columns: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SheetRow(Base):
    __tablename__ = "sheet_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id"), index=True)
    row_index: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
