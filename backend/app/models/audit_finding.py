from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditFindingType(StrEnum):
    NONCONFORMITY = "nonconformity"
    OBSERVATION = "observation"


class AuditFinding(Base):
    """One thing found during an InternalAudit. Carries no forward link to
    a CorrectiveAction raised from it -- CorrectiveAction already has a
    (source_type, source_id) pair built for exactly this ("an internal-audit
    finding with no tracked record behind it"), so the link is looked up in
    that direction (corrective_action_service.list_for_source), the same
    way nothing points forward from a DocumentChunk's source either."""

    __tablename__ = "audit_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_audit_id: Mapped[int] = mapped_column(ForeignKey("internal_audits.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    finding_type: Mapped[str] = mapped_column(String(20), default=AuditFindingType.OBSERVATION)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
