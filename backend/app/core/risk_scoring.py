"""Canonical risk scoring rules.

Severity bands and the overdue rule live here so the dashboard counts, the
risk matrix shading, and the per-row "Overdue" flag can never disagree.

The band boundaries are organization-configurable (see risk_criteria_service);
every function here takes a ``Bands`` and falls back to ``DEFAULT_BANDS`` so
callers that genuinely have no criteria still behave sensibly.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.models.risk_criteria import DEFAULT_HIGH_MIN_SCORE, DEFAULT_MEDIUM_MIN_SCORE

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# Free-text status values treated as "no longer outstanding" for overdue
# purposes -- the status column has no enforced set of values, so this is a
# best-effort match rather than a strict enum.
TREATED_STATUSES = frozenset(
    {"treated", "closed", "resolved", "completed", "done", "mitigated"}
)


@dataclass(frozen=True)
class Bands:
    """Inclusive lower bounds for the medium and high severity bands."""

    medium_min_score: int = DEFAULT_MEDIUM_MIN_SCORE
    high_min_score: int = DEFAULT_HIGH_MIN_SCORE


DEFAULT_BANDS = Bands()


def severity_for_score(score: float, bands: Bands = DEFAULT_BANDS) -> str:
    if score >= bands.high_min_score:
        return SEVERITY_HIGH
    if score >= bands.medium_min_score:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def is_high_risk(score: float, bands: Bands = DEFAULT_BANDS) -> bool:
    return score >= bands.high_min_score


def numeric(value: Any) -> float | None:
    """Coerce a sheet cell to a number, tolerating numeric strings."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def level(value: Any) -> int | None:
    """Coerce a likelihood/impact cell to a 1..5 matrix level."""
    num = numeric(value)
    if num is None:
        return None
    return min(5, max(1, round(num)))


def is_treated(status: Any) -> bool:
    return isinstance(status, str) and status.strip().lower() in TREATED_STATUSES


def is_overdue(row_data: dict[str, Any], today: date | None = None) -> bool:
    """A risk item is overdue when its treatment deadline has passed and it is
    not yet in a treated status."""
    deadline = row_data.get("treatment_deadline")
    if not isinstance(deadline, str) or not deadline.strip():
        return False
    try:
        deadline_date = datetime.fromisoformat(deadline.strip()).date()
    except ValueError:
        return False

    if is_treated(row_data.get("status")):
        return False

    reference = today if today is not None else datetime.now(UTC).date()
    return deadline_date < reference
