"""EU AI Act Article 73 serious-incident reporting deadlines.

A serious incident must be reported to the market surveillance authority
within a deadline counted from when the organization became aware of it,
and how long depends on what happened:

- Art. 73(3): a widespread infringement, or a serious and irreversible
  disruption of critical infrastructure -- 2 days.
- Art. 73(4): the death of a person -- 10 days.
- Art. 73(2): any other serious incident -- 15 days.

Pure functions, kept apart from the service like audit_schedule is: the
deadline and whether it's been missed are computed live from an incident's
own fields, never stored, so they can't disagree with them.
"""

from datetime import date, timedelta
from enum import StrEnum


class SeriousIncidentCategory(StrEnum):
    WIDESPREAD_OR_CRITICAL_INFRASTRUCTURE = "widespread_or_critical_infrastructure"
    DEATH = "death"
    OTHER = "other"


REPORTING_DAYS: dict[str, int] = {
    SeriousIncidentCategory.WIDESPREAD_OR_CRITICAL_INFRASTRUCTURE: 2,
    SeriousIncidentCategory.DEATH: 10,
    SeriousIncidentCategory.OTHER: 15,
}


def reporting_deadline(is_serious: bool, category: str | None, detected_on: date) -> date | None:
    """The last day the authority can be notified -- None for an incident
    that isn't serious, since only serious incidents are reportable."""
    if not is_serious or category not in REPORTING_DAYS:
        return None
    return detected_on + timedelta(days=REPORTING_DAYS[category])


def is_reporting_overdue(
    is_serious: bool,
    category: str | None,
    detected_on: date,
    authority_notified_on: date | None,
    today: date,
) -> bool:
    """Overdue once the deadline has passed with no notification recorded.
    A notification made late still stops it being overdue -- the report has
    been made; its lateness stays visible in the dates themselves."""
    if authority_notified_on is not None:
        return False
    deadline = reporting_deadline(is_serious, category, detected_on)
    return deadline is not None and deadline < today
