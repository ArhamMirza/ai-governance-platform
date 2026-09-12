"""Shared review cadence for everything that gets approved.

ISO 42001 expects impact and risk assessments to be performed before an AI
system goes into use and re-performed at planned intervals, and expects the
same of the policies and procedures governing it. All four use the same yearly
cadence and the same helpers so their dates stay aligned -- an organization
reviewing one but not the others is exactly the drift this is meant to
prevent.
"""

from datetime import date

REVIEW_INTERVAL_YEARS = 1


def next_review_date(assessment_date: date) -> date:
    """One year on. Feb 29 lands on Feb 28 in a non-leap year rather than
    raising, which is the conventional anniversary handling."""
    try:
        return assessment_date.replace(year=assessment_date.year + REVIEW_INTERVAL_YEARS)
    except ValueError:
        return assessment_date.replace(
            year=assessment_date.year + REVIEW_INTERVAL_YEARS, day=28
        )


def is_review_overdue(review_date: date | None, today: date) -> bool:
    return review_date is not None and review_date < today
