from app.core import risk_scoring
from app.models.sheet import SheetRow
from app.services import risk_analytics_service

PAST_DEADLINE = "2020-01-01"
FUTURE_DEADLINE = "2099-01-01"


def row(row_id: int = 1, **data) -> SheetRow:
    return SheetRow(id=row_id, sheet_id=1, row_index=row_id, data=data)


def test_inherent_score_falls_back_to_likelihood_times_impact() -> None:
    assert risk_analytics_service.inherent_score(row(likelihood=4, impact=3)) == 12


def test_inherent_score_prefers_the_stored_value() -> None:
    scored = row(likelihood=4, impact=3, inherent_risk_score=20)

    assert risk_analytics_service.inherent_score(scored) == 20


def test_scores_tolerate_numeric_strings() -> None:
    assert risk_analytics_service.inherent_score(row(likelihood="4", impact="3")) == 12


def test_missing_inputs_produce_no_score() -> None:
    assert risk_analytics_service.inherent_score(row(likelihood=4)) is None
    assert risk_analytics_service.inherent_score(row()) is None


def test_summarize_rows_buckets_by_severity() -> None:
    summary = risk_analytics_service.summarize_rows(
        [
            row(1, likelihood=5, impact=5),  # 25 high
            row(2, likelihood=3, impact=3),  # 9 medium
            row(3, likelihood=2, impact=2),  # 4 low
        ]
    )

    assert summary.total == 3
    assert summary.by_severity == {"high": 1, "medium": 1, "low": 1}


def test_summarize_rows_honours_custom_bands() -> None:
    rows = [row(1, likelihood=3, impact=3)]  # score 9

    default = risk_analytics_service.summarize_rows(rows)
    strict = risk_analytics_service.summarize_rows(
        rows, risk_scoring.Bands(medium_min_score=3, high_min_score=9)
    )

    assert default.by_severity["medium"] == 1
    assert strict.by_severity["high"] == 1


def test_summarize_rows_counts_overdue_and_untreated() -> None:
    summary = risk_analytics_service.summarize_rows(
        [
            row(1, likelihood=4, impact=4, treatment_deadline=PAST_DEADLINE),
            row(2, likelihood=4, impact=4, treatment_deadline=FUTURE_DEADLINE),
            # Past deadline but already treated, so not overdue.
            row(3, likelihood=4, impact=4, treatment_deadline=PAST_DEADLINE, status="Closed"),
        ]
    )

    assert summary.overdue_count == 1
    assert summary.untreated_count == 2


def test_summarize_rows_averages_inherent_and_residual() -> None:
    summary = risk_analytics_service.summarize_rows(
        [
            row(1, likelihood=4, impact=4, residual_likelihood=2, residual_impact=2),
            row(2, likelihood=2, impact=2, residual_likelihood=1, residual_impact=1),
        ]
    )

    assert summary.average_inherent_score == 10.0
    assert summary.average_residual_score == 2.5


def test_summarize_empty_rows() -> None:
    summary = risk_analytics_service.summarize_rows([])

    assert summary.total == 0
    assert summary.by_severity == {"high": 0, "medium": 0, "low": 0}
    assert summary.average_inherent_score is None


def test_matrix_cells_only_reports_occupied_cells() -> None:
    cells = risk_analytics_service.matrix_cells(
        [
            row(1, likelihood=4, impact=3),
            row(2, likelihood=4, impact=3),
            row(3, likelihood=1, impact=1),
            row(4, likelihood=None, impact=3),
        ]
    )

    assert [(c.likelihood, c.impact, c.count) for c in cells] == [(1, 1, 1), (4, 3, 2)]


def test_matrix_levels_are_clamped_to_the_grid() -> None:
    cells = risk_analytics_service.matrix_cells([row(1, likelihood=9, impact=0)])

    assert (cells[0].likelihood, cells[0].impact) == (5, 1)


def test_overall_rating_is_the_worst_inherent_score() -> None:
    rating = risk_analytics_service.overall_rating(
        [row(1, likelihood=2, impact=2), row(2, likelihood=5, impact=4)]
    )

    assert rating == 20


def test_overall_rating_without_scores() -> None:
    assert risk_analytics_service.overall_rating([row(1)]) is None
