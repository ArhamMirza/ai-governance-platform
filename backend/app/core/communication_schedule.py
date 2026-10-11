"""When a planned communication is next due -- ISO/IEC 42001 7.4. Pure
functions, computed live from the plan item's own fields and the dates it
was actually carried out, never stored, so they can't disagree with them.

The rule is the one internal audits and supplier reviews already use
(app.core.audit_schedule): due on first_due until the first record, then
interval_months on from the latest one. A communication with no interval is
event-driven (say, notifying customers of an incident) and is never "due".
"""

from datetime import date

from app.core import audit_schedule


def next_due(
    interval_months: int | None, first_due: date | None, communicated_dates: list[date]
) -> date | None:
    if interval_months is None:
        return None
    if not communicated_dates:
        return first_due
    return audit_schedule.next_audit_date(max(communicated_dates), interval_months)


def is_overdue(is_active: bool, next_due_date: date | None, today: date) -> bool:
    """A communication the organization has stopped doing isn't due."""
    return is_active and audit_schedule.is_audit_overdue(next_due_date, today)
