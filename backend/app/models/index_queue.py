"""Sources whose text has changed and whose index is therefore out of date.

Indexing a record is not free -- rendering, chunking and embedding cost tens
of milliseconds -- and a sheet import writes hundreds of rows in one
transaction. Doing the work inline would make every edit wait on it.

So a write only records *that* the source is stale, which is one cheap
insert, and the work happens later. The row is written in the same
transaction as the change that caused it, so a committed edit and its
pending reindex are never out of step: either both happened or neither did.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndexQueueEntry(Base):
    __tablename__ = "index_queue"
    # One pending entry per source. A record edited ten times before the
    # queue is drained is reindexed once, from its final state.
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_index_queue_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(Integer)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
