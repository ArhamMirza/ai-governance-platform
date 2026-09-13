from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AiProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    # Anything speaking an OpenAI-shaped API on a URL the org controls --
    # Ollama, vLLM, LM Studio. The one provider where no request leaves the
    # deployment at all.
    LOCAL = "local"


# Sensible starting points per provider, offered by the settings UI. The
# admin can type any model name their provider accepts -- this is a
# convenience, not an allowlist, so a model released next week still works
# without a code change.
SUGGESTED_MODELS: dict[str, str] = {
    AiProvider.ANTHROPIC: "claude-sonnet-5",
    AiProvider.OPENAI: "gpt-5.1",
    AiProvider.GEMINI: "gemini-2.5-pro",
    AiProvider.GROQ: "llama-3.3-70b-versatile",
    AiProvider.LOCAL: "llama3.3",
}


class AiAssistSettings(Base):
    """Which model the organization's AI assistance runs on. A single row,
    the same shape RiskCriteria uses -- one org-wide choice an admin makes,
    not a per-user preference, since the API key is an organizational
    credential and its spend is an organizational cost."""

    __tablename__ = "ai_assist_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), default=AiProvider.ANTHROPIC)
    model: Mapped[str] = mapped_column(String(120), default="")

    # The cheap tier, used for summarizing and classifying rather than
    # generating. Falls back to `model` when unset, so an org that doesn't
    # care about the distinction doesn't have to think about it.
    fast_model: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Encrypted (app.core.crypto) -- never returned by the API, which
    # reports only whether one is present.
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Only meaningful for LOCAL: where that OpenAI-shaped endpoint lives.
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Per user, per day. Bounds both cost and the blast radius of a runaway
    # loop; 0 disables assistance entirely without clearing the key.
    daily_token_budget: Mapped[int] = mapped_column(Integer, default=200_000)

    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AiUsage(Base):
    """One row per model call: who, what for, and what it cost in tokens.

    Cost visibility, the data the daily budget is enforced against, and --
    in a platform whose whole job is governing AI -- a record of how this
    deployment's own AI is being used."""

    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    # "draft_field", "chat", "summarize" -- which surface spent the tokens.
    feature: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(120))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
