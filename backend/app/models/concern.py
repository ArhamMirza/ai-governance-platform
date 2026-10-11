from datetime import date
from enum import StrEnum

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConcernCategory(StrEnum):
    SAFETY_OR_HARM = "safety_or_harm"
    BIAS_OR_FAIRNESS = "bias_or_fairness"
    PRIVACY_OR_DATA = "privacy_or_data"
    MISUSE_OR_BREACH = "misuse_or_breach"
    TRANSPARENCY = "transparency"
    ACCURACY_OR_RELIABILITY = "accuracy_or_reliability"
    OTHER = "other"


class ConcernChannel(StrEnum):
    # Through the employee home.
    EMPLOYEE_PORTAL = "employee_portal"
    # The rest are logged by a handler for someone who raised it another way.
    PHONE = "phone"
    EMAIL = "email"
    IN_PERSON = "in_person"
    OTHER = "other"


class ConcernStatus(StrEnum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    NOT_ACTIONED = "not_actioned"


class ConcernOutcome(StrEnum):
    SUBSTANTIATED = "substantiated"
    PARTLY_SUBSTANTIATED = "partly_substantiated"
    NOT_SUBSTANTIATED = "not_substantiated"
    NO_FINDING = "no_finding"


class Concern(Base):
    """A concern someone raised about the organization's role in relation to an
    AI system -- ISO/IEC 42001 A.3.3.

    Deliberately carries **no timestamps**: only `received_on`, a date. A
    concern raised anonymously stores no reporter at all, and a precise
    created_at would let someone with database access match it to when a
    particular person was signed in. The same reasoning keeps the audit log
    from recording an anonymous submission (see concern_service).

    Visible only to the people handling concerns; the reporter sees their own
    through the employee home (status and the handler's reply, never
    internal_notes or closure_note)."""

    __tablename__ = "concerns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(30), default=ConcernCategory.OTHER)
    description: Mapped[str] = mapped_column(Text)
    ai_system_row_id: Mapped[int | None] = mapped_column(
        ForeignKey("sheet_rows.id"), nullable=True, index=True
    )
    # "Not sure which system" -- free text from the reporter.
    system_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default=ConcernChannel.EMPLOYEE_PORTAL)
    received_on: Mapped[date] = mapped_column(Date)

    # Null when the concern is anonymous, always -- never "hidden", absent.
    reporter_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    # What a person who raised it by phone, email or in person agreed to
    # share, as the handler recorded it.
    reporter_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 of the tracking code; the code itself is never kept.
    tracking_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default=ConcernStatus.RECEIVED)
    handler_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acknowledged_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the reporter can read.
    reply_to_reporter: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The incident raised from it, if any (an AIIncident id).
    incident_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ConcernSettings(Base):
    """How reporting works here: what employees are told, and how quickly a
    concern must be acknowledged. One row, like ManagementReviewSettings."""

    __tablename__ = "concern_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledge_within_days: Mapped[int] = mapped_column(Integer, default=7)
