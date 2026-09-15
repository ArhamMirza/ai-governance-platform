from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationStart(BaseModel):
    # The record on screen when the conversation was opened, if any.
    context_entity_type: str | None = None
    context_entity_id: int | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    context_entity_type: str | None
    context_entity_id: int | None
    created_at: datetime
    updated_at: datetime


class CitationRead(BaseModel):
    """A source an answer cited, after checking it was actually provided."""

    n: int
    chunk_id: int
    source_type: str
    source_id: int
    title: str
    section: str | None = None
    read_by_ocr: bool = False
    entity_type: str
    entity_id: int
    # Where in the application the cited record can be opened.
    href: str | None = None
    download_evidence_id: int | None = None
    excerpt: str
    injection_findings: list[str] = []


class CoverageGapRead(BaseModel):
    evidence_id: int
    filename: str
    detail: str | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list[CitationRead] | None = None
    # Source numbers the model cited without having been given them, removed
    # from the answer before it was shown.
    fabricated_citations: list[int] | None = None
    injection_findings: list[str] | None = None
    coverage_gaps: list[CoverageGapRead] | None = None
    retrieval_mode: str | None = None
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
