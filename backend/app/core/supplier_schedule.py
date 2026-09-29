"""When a supplier's next review is due, and whether its contract needs
attention. Pure functions, computed live from a supplier's own fields and
review dates -- never stored, so they can't disagree with them.

Review timing is the same rule as internal audits and management review
(app.core.audit_schedule): due on first_review_due until the first review,
then interval_months on from the latest one.
"""

from datetime import date, timedelta
from typing import Literal

from app.core import audit_schedule

CONTRACT_EXPIRY_WARNING_DAYS = 30

ContractStatus = Literal["expired", "expiring"]


def next_review_due(
    interval_months: int | None, first_review_due: date | None, review_dates: list[date]
) -> date | None:
    if interval_months is None:
        return None
    if not review_dates:
        return first_review_due
    return audit_schedule.next_audit_date(max(review_dates), interval_months)


def is_review_overdue(is_active: bool, next_due: date | None, today: date) -> bool:
    """A supplier the organization has stopped using isn't due a review."""
    return is_active and audit_schedule.is_audit_overdue(next_due, today)


def contract_status(
    is_active: bool, contract_end: date | None, today: date
) -> ContractStatus | None:
    """Expired once the end date has passed, expiring within the warning
    window before it (the end date itself included), else None. Inactive
    suppliers never alert -- an ended contract is expected there."""
    if not is_active or contract_end is None:
        return None
    if contract_end < today:
        return "expired"
    if contract_end <= today + timedelta(days=CONTRACT_EXPIRY_WARNING_DAYS):
        return "expiring"
    return None
