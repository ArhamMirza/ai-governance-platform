from datetime import date

import pytest

from app.core import incident_reporting
from app.core.incident_reporting import SeriousIncidentCategory

DETECTED = date(2026, 3, 1)


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (SeriousIncidentCategory.WIDESPREAD_OR_CRITICAL_INFRASTRUCTURE, date(2026, 3, 3)),
        (SeriousIncidentCategory.DEATH, date(2026, 3, 11)),
        (SeriousIncidentCategory.OTHER, date(2026, 3, 16)),
    ],
)
def test_each_category_sets_its_article_73_deadline(category: str, expected: date) -> None:
    assert incident_reporting.reporting_deadline(True, category, DETECTED) == expected


def test_an_incident_that_is_not_serious_has_no_deadline() -> None:
    assert incident_reporting.reporting_deadline(False, None, DETECTED) is None


def test_not_overdue_on_the_deadline_itself() -> None:
    assert not incident_reporting.is_reporting_overdue(
        True, SeriousIncidentCategory.DEATH, DETECTED, None, date(2026, 3, 11)
    )


def test_overdue_the_day_after_the_deadline_with_no_notification() -> None:
    assert incident_reporting.is_reporting_overdue(
        True, SeriousIncidentCategory.DEATH, DETECTED, None, date(2026, 3, 12)
    )


def test_recording_the_notification_stops_it_being_overdue() -> None:
    assert not incident_reporting.is_reporting_overdue(
        True, SeriousIncidentCategory.DEATH, DETECTED, date(2026, 3, 20), date(2026, 4, 1)
    )


def test_an_incident_that_is_not_serious_is_never_overdue() -> None:
    assert not incident_reporting.is_reporting_overdue(
        False, None, DETECTED, None, date(2027, 1, 1)
    )
