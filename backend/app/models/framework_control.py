from enum import StrEnum

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Framework(StrEnum):
    ISO_42001 = "iso_42001"
    EU_AI_ACT = "eu_ai_act"


class FrameworkControl(Base):
    """Reference data: a single clause/article an organization can tag work
    against (e.g. ISO 42001 clause 8.4, EU AI Act Article 9). Seeded once via
    migration -- not user-editable."""

    __tablename__ = "framework_controls"
    __table_args__ = (UniqueConstraint("framework", "code", name="uq_framework_control_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    framework: Mapped[str] = mapped_column(String(30), index=True)
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "clause" (ISO main body 4-10, EU AI Act articles) or "annex_a_control"
    # (the 38 Annex A controls a Statement of Applicability is built over).
    category: Mapped[str] = mapped_column(String(20), default="clause")
