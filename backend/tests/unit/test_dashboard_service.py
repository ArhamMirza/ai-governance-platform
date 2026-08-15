from unittest.mock import MagicMock, patch

import pytest

from app.models.policy import Policy, PolicyStatus
from app.models.procedure import Procedure, ProcedureStatus
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.sheet import SheetRow
from app.services import dashboard_service


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


def make_risk_assessment(**overrides) -> RiskAssessment:
    defaults = dict(
        id=1,
        ai_system_row_id=1,
        sheet_id=1,
        framework_tags=[],
        status=RiskAssessmentStatus.DRAFT,
        assessor_id=None,
        assessment_date=None,
    )
    defaults.update(overrides)
    return RiskAssessment(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.dashboard_service.risk_assessment_service")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_counts_by_status(
    mock_policy_repo, mock_procedure_repo, mock_inventory, mock_ra_repo, mock_ra_service, db
) -> None:
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
    mock_ra_service.compute_overall_risk_rating.return_value = None

    result = dashboard_service.get_summary(db)

    assert result.policies.total == 3
    assert result.policies.by_status == {"draft": 2, "approved": 1}
    assert result.procedures.total == 1
    assert result.procedures.by_status == {"in_review": 1}
    assert result.ai_systems.total == 3
    assert result.ai_systems.by_risk_tier == {"high": 2, "unspecified": 1}
    assert result.risk_assessments.total == 1
    assert result.risk_assessments.by_status == {"draft": 1}


@patch("app.services.dashboard_service.risk_assessment_service")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_counts_high_risk_assessments(
    mock_policy_repo, mock_procedure_repo, mock_inventory, mock_ra_repo, mock_ra_service, db
) -> None:
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = [
        make_risk_assessment(id=1, sheet_id=1),
        make_risk_assessment(id=2, sheet_id=2),
        make_risk_assessment(id=3, sheet_id=3),
    ]
    mock_ra_service.compute_overall_risk_rating.side_effect = [20.0, 6.0, None]

    result = dashboard_service.get_summary(db)

    assert result.risk_assessments.high_risk_count == 1


@patch("app.services.dashboard_service.risk_assessment_service")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
def test_get_summary_handles_empty_data(
    mock_policy_repo, mock_procedure_repo, mock_inventory, mock_ra_repo, mock_ra_service, db
) -> None:
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = []

    result = dashboard_service.get_summary(db)

    assert result.policies.total == 0
    assert result.policies.by_status == {}
    assert result.ai_systems.by_risk_tier == {}
    assert result.risk_assessments.high_risk_count == 0
