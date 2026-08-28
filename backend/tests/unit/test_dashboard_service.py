from unittest.mock import MagicMock, patch

import pytest

from app.core import risk_scoring
from app.models.policy import Policy, PolicyStatus
from app.models.procedure import Procedure, ProcedureStatus
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.sheet import SheetRow
from app.services import dashboard_service

PAST_DEADLINE = "2020-01-01"
FUTURE_DEADLINE = "2099-01-01"


def make_policy(**overrides) -> Policy:
    defaults = dict(id=1, title="P", description=None, owner_id=None, effective_date=None)
    defaults.update(overrides)
    return Policy(**defaults)


def make_procedure(**overrides) -> Procedure:
    defaults = dict(
        id=1, title="P", description=None, owner_id=None, policy_id=None, effective_date=None
    )
    defaults.update(overrides)
    return Procedure(**defaults)


def make_ai_system_row(**overrides) -> SheetRow:
    defaults = dict(id=1, sheet_id=1, row_index=1, data={})
    defaults.update(overrides)
    return SheetRow(**defaults)


def make_risk_row(likelihood: int, impact: int, **data) -> SheetRow:
    return SheetRow(
        id=data.pop("id", 1),
        sheet_id=data.pop("sheet_id", 1),
        row_index=data.pop("row_index", 1),
        data={
            "likelihood": likelihood,
            "impact": impact,
            "inherent_risk_score": likelihood * impact,
            **data,
        },
    )


def make_risk_assessment(**overrides) -> RiskAssessment:
    defaults = dict(
        id=1,
        ai_system_row_id=1,
        sheet_id=1,
        status=RiskAssessmentStatus.DRAFT,
        assessor_id=None,
        assessment_date=None,
    )
    defaults.update(overrides)
    return RiskAssessment(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_counts_by_status(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = [
        make_policy(status=PolicyStatus.DRAFT),
        make_policy(id=2, status=PolicyStatus.DRAFT),
        make_policy(id=3, status=PolicyStatus.APPROVED),
    ]
    mock_procedure_repo.list_all.return_value = [
        make_procedure(status=ProcedureStatus.IN_REVIEW),
    ]
    mock_inventory.list_rows.return_value = [
        make_ai_system_row(data={"risk_tier": "high"}),
        make_ai_system_row(id=2, data={"risk_tier": "high"}),
        make_ai_system_row(id=3, data={}),
    ]
    mock_ra_repo.list_all.return_value = [
        make_risk_assessment(status=RiskAssessmentStatus.DRAFT),
    ]
    mock_sheet_repo.list_rows_for_sheets.return_value = {1: []}

    result = dashboard_service.get_summary(db, actor_id=99)

    assert result.policies.total == 3
    assert result.policies.by_status == {"draft": 2, "approved": 1}
    assert result.procedures.total == 1
    assert result.procedures.by_status == {"in_review": 1}
    assert result.ai_systems.total == 3
    assert result.ai_systems.by_risk_tier == {"high": 2, "unspecified": 1}
    assert result.risk_assessments.total == 1
    assert result.risk_assessments.by_status == {"draft": 1}


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_counts_high_risk_assessments(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = [
        make_risk_assessment(id=1, sheet_id=1),
        make_risk_assessment(id=2, sheet_id=2),
        make_risk_assessment(id=3, sheet_id=3),
    ]
    mock_sheet_repo.list_rows_for_sheets.return_value = {
        1: [make_risk_row(5, 4, sheet_id=1)],  # 20 -> high
        2: [make_risk_row(2, 3, sheet_id=2)],  # 6  -> medium
        3: [],  # unrated
    }

    result = dashboard_service.get_summary(db, actor_id=99)

    assert result.risk_assessments.high_risk_count == 1


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_uses_configured_bands(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    """A score of 8 is medium by default but high once the org lowers the band."""
    mock_criteria.get_bands.return_value = risk_scoring.Bands(
        medium_min_score=4, high_min_score=8
    )
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = [make_risk_assessment(id=1, sheet_id=1)]
    mock_sheet_repo.list_rows_for_sheets.return_value = {
        1: [make_risk_row(4, 2, sheet_id=1)],  # score 8
    }

    result = dashboard_service.get_summary(db, actor_id=99)

    assert result.risk_assessments.high_risk_count == 1
    assert result.risk_items.by_severity["high"] == 1


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_reports_risk_items_and_coverage(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = [make_policy(status=PolicyStatus.APPROVED)]
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = [
        make_ai_system_row(id=1),
        make_ai_system_row(id=2),
    ]
    mock_ra_repo.list_all.return_value = [
        make_risk_assessment(id=1, sheet_id=1, ai_system_row_id=1),
    ]
    mock_sheet_repo.list_rows_for_sheets.return_value = {
        1: [
            make_risk_row(5, 4, sheet_id=1, treatment_deadline=PAST_DEADLINE),
            make_risk_row(2, 3, id=2, sheet_id=1, treatment_deadline=FUTURE_DEADLINE),
            make_risk_row(1, 2, id=3, sheet_id=1, status="closed"),
        ]
    }

    result = dashboard_service.get_summary(db, actor_id=99)

    assert result.risk_items.total == 3
    assert result.risk_items.by_severity == {"high": 1, "medium": 1, "low": 1}
    assert result.risk_items.overdue_count == 1
    assert result.risk_items.untreated_count == 2
    # Only one of the two AI systems has an assessment.
    assert result.coverage.ai_systems_total == 2
    assert result.coverage.ai_systems_assessed == 1
    assert result.coverage.policies_approved == 1


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.impact_assessment_repository")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_attention_lists_only_nonzero_items(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_impact_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = [make_ai_system_row(id=1)]
    mock_ra_repo.list_all.return_value = []
    mock_sheet_repo.list_rows_for_sheets.return_value = {}
    mock_impact_repo.list_all.return_value = []

    result = dashboard_service.get_summary(db, actor_id=99)

    keys = {item.key: item.count for item in result.attention}
    # The one AI system has neither an impact nor a risk assessment.
    assert keys == {"no_impact_assessment": 1, "unassessed_ai_systems": 1}


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_handles_empty_data(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = []
    mock_sheet_repo.list_rows_for_sheets.return_value = {}

    result = dashboard_service.get_summary(db, actor_id=99)

    assert result.policies.total == 0
    assert result.policies.by_status == {}
    assert result.ai_systems.by_risk_tier == {}
    assert result.risk_assessments.high_risk_count == 0
    assert result.risk_items.total == 0
    assert result.risk_items.average_inherent_score is None
    assert result.attention == []
    assert result.matrix == []
    assert result.my_risk_items == []


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_my_risk_items_matches_owner_and_excludes_closed(
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = [make_risk_assessment(id=1, sheet_id=1)]
    mock_sheet_repo.list_rows_for_sheets.return_value = {
        1: [
            # Owned by me, overdue and open -- should appear.
            make_risk_row(
                4, 4, id=1, sheet_id=1, risk_owner="99",
                treatment_deadline=PAST_DEADLINE, status="open",
            ),
            # Owned by me but already closed -- should be excluded.
            make_risk_row(2, 2, id=2, sheet_id=1, risk_owner="99", status="closed"),
            # Owned by someone else -- should be excluded.
            make_risk_row(3, 3, id=3, sheet_id=1, risk_owner="1", status="open"),
            # Unassigned -- should be excluded.
            make_risk_row(1, 1, id=4, sheet_id=1, status="open"),
        ]
    }

    result = dashboard_service.get_summary(db, actor_id=99)

    assert [item.row_id for item in result.my_risk_items] == [1]
    assert result.my_risk_items[0].risk_assessment_id == 1
    assert result.my_risk_items[0].overdue is True
