from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EuAiActApplicability(Base):
    """The organization's own assessment of whether, and how, the EU AI Act
    applies to it. A singleton, like RiskCriteria -- no row until someone
    records an assessment, which reads the same as in_scope=None.

    What each answer means for individual articles lives in
    app.core.eu_ai_act_scope.
    """

    __tablename__ = "eu_ai_act_applicability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # None = not assessed yet (every article applies until it is).
    in_scope: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    scope_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Value-chain roles -- an organization can hold several (e.g. provider
    # of its own models and deployer of a vendor's).
    is_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deployer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_importer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_distributor: Mapped[bool] = mapped_column(Boolean, default=False)

    # Asked rather than derived from the inventory's free-text Risk Tier
    # column: a typo there must not silently remove obligations.
    has_high_risk_systems: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
