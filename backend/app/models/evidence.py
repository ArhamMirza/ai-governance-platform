from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set when a document is uploaded to satisfy a life cycle stage gate --
    # see app.core.document_types. Null for ordinary evidence.
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    # Whether the assistant can see this file, and why not when it can't --
    # see app.models.document_chunk.IndexStatus. Reported to the user rather
    # than kept internal: a document nobody can search is a gap in the
    # record, and a silent gap is the dangerous kind.
    index_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    index_detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Text inside the document written to instruct a model, found at index
    # time. Kept on the record because it is a governance finding about the
    # document, not a transient detail of one search.
    injection_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
