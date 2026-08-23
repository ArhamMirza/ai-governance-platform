"""Aggregations over individual risk items.

The dashboard and the risk assessment portfolio view both need counts derived
from risk item rows rather than from assessments, so the maths lives here once.
"""

from collections import Counter
from collections.abc import Iterable

from app.core import risk_scoring
from app.models.sheet import SheetRow
from app.schemas.dashboard import MatrixCell, RiskItemSummary

SEVERITIES = (
    risk_scoring.SEVERITY_HIGH,
    risk_scoring.SEVERITY_MEDIUM,
    risk_scoring.SEVERITY_LOW,
)


def inherent_score(row: SheetRow) -> float | None:
    """The stored inherent score, falling back to likelihood x impact."""
    score = risk_scoring.numeric(row.data.get("inherent_risk_score"))
    if score is not None:
        return score

    likelihood = risk_scoring.numeric(row.data.get("likelihood"))
    impact = risk_scoring.numeric(row.data.get("impact"))
    if likelihood is None or impact is None:
        return None
    return likelihood * impact


def residual_score(row: SheetRow) -> float | None:
    score = risk_scoring.numeric(row.data.get("residual_risk_score"))
    if score is not None:
        return score

    likelihood = risk_scoring.numeric(row.data.get("residual_likelihood"))
    impact = risk_scoring.numeric(row.data.get("residual_impact"))
    if likelihood is None or impact is None:
        return None
    return likelihood * impact


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def summarize_rows(
    rows: Iterable[SheetRow], bands: risk_scoring.Bands = risk_scoring.DEFAULT_BANDS
) -> RiskItemSummary:
    rows = list(rows)
    severity_counts: Counter[str] = Counter()
    inherent_scores: list[float] = []
    residual_scores: list[float] = []
    overdue_count = 0
    untreated_count = 0

    for row in rows:
        score = inherent_score(row)
        if score is not None:
            severity_counts[risk_scoring.severity_for_score(score, bands)] += 1
            inherent_scores.append(score)

        residual = residual_score(row)
        if residual is not None:
            residual_scores.append(residual)

        if risk_scoring.is_overdue(row.data):
            overdue_count += 1
        if not risk_scoring.is_treated(row.data.get("status")):
            untreated_count += 1

    return RiskItemSummary(
        total=len(rows),
        by_severity={severity: severity_counts.get(severity, 0) for severity in SEVERITIES},
        overdue_count=overdue_count,
        untreated_count=untreated_count,
        average_inherent_score=_mean(inherent_scores),
        average_residual_score=_mean(residual_scores),
    )


def matrix_cells(rows: Iterable[SheetRow]) -> list[MatrixCell]:
    """Occupied 5x5 cells only -- the client renders the empty ones."""
    counts: Counter[tuple[int, int]] = Counter()
    for row in rows:
        likelihood = risk_scoring.level(row.data.get("likelihood"))
        impact = risk_scoring.level(row.data.get("impact"))
        if likelihood is None or impact is None:
            continue
        counts[(likelihood, impact)] += 1

    return [
        MatrixCell(likelihood=likelihood, impact=impact, count=count)
        for (likelihood, impact), count in sorted(counts.items())
    ]


def overall_rating(rows: Iterable[SheetRow]) -> float | None:
    scores = [score for row in rows if (score := inherent_score(row)) is not None]
    return max(scores) if scores else None
