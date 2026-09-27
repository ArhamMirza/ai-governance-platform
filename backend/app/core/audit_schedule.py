"""User-configurable recurrence for internal audit programs.

Unlike review_cadence.py's fixed one-year cadence (shared by every
approval-triggered review in the system), an audit program's interval is
something the organization sets for itself -- audits happen as often as the
management system's own audit plan calls for, not on one cadence everyone
shares. Kept separate rather than stretching review_cadence.py past the one
thing it's scoped to.
"""

from datetime import date


def next_audit_date(from_date: date, interval_months: int) -> date:
    """`interval_months` on from `from_date`, clamping the day when the
    target month is shorter (the 31st of a 3-month interval from a 31-day
    month lands on the last day of a shorter one, not an error)."""
    total_months = from_date.month - 1 + interval_months
    year = from_date.year + total_months // 12
    month = total_months % 12 + 1
    day = min(from_date.day, _days_in_month(year, month))
    return from_date.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    return (next_month_first - date(year, month, 1)).days


def is_audit_overdue(next_due_date: date | None, today: date) -> bool:
    return next_due_date is not None and next_due_date < today
