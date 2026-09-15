"""Conversations with the assistant, and what it said in them.

Every conversation belongs to exactly one person, and nothing reads one
person's conversations on another's behalf -- not the assistant recalling
earlier chats, not an admin, not a search. What someone asks an assistant
while working through a sensitive assessment is theirs.

An assistant message stores the citations it was *allowed* to show, after
verification, alongside a record of anything that was stripped for citing a
source it was never given. The second list exists for the same reason the
audit log does: when an answer is later questioned, "the model invented a
source and we removed it" is a fact worth being able to show.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AiConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    # Where the conversation was started -- the AI system or policy on screen
    # at the time -- so the assistant can read that record exactly rather
    # than hoping a search surfaces it.
    context_entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    context_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # A running summary of the turns that have scrolled out of the verbatim
    # window, so a long conversation keeps its thread without the prompt
    # growing with every message.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summarized_through_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The summary's embedding, for recalling this conversation from a later
    # one. Only ever compared against the same person's other conversations.
    summary_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AiMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    # Verified citations only: each one names a passage that was actually
    # retrieved for this turn and quoted to the model.
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Source numbers the model cited that it was never given. Removed from
    # the answer before anyone saw it, and kept here as the record of that.
    fabricated_citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Text that reads as an instruction to a model -- in the question, or in
    # a source quoted to answer it.
    injection_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Documents in scope that search could not read, reported with the answer
    # so "nothing found" is never mistaken for "nothing there".
    coverage_gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    retrieval_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
