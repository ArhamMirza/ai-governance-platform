from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.sheet import SheetRow
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.services import risk_assessment_service


def make_risk_assessment(**overrides) -> RiskAssessment:
    defaults = dict(
        id=1,
        ai_system_row_id=10,
        sheet_id=5,
        status=RiskAssessmentStatus.DRAFT,
        assessor_id=None,
        assessment_date=None,
    )
    defaults.update(overrides)
    return RiskAssessment(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.risk_assessment_service.audit_service")
@patch("app.services.risk_assessment_service.sheet_service")
@patch("app.services.risk_assessment_service.risk_assessment_repository")
@patch("app.services.risk_assessment_service.ai_system_inventory_service")
@patch("app.services.risk_assessment_service.sheet_repository")
def test_create_risk_assessment_validates_ai_system_row(
    mock_sheet_repo, mock_inventory, mock_repo, mock_sheet_service, mock_audit, db
) -> None:
    mock_inventory.get_or_create_sheet.return_value = MagicMock(id=99)
    mock_sheet_repo.get_row.return_value = SheetRow(id=10, sheet_id=99, row_index=1, data={})
    mock_sheet_service.create_sheet.return_value = MagicMock(id=5)
    mock_repo.create.side_effect = lambda _db, ra: ra

    result = risk_assessment_service.create_risk_assessment(
        db, RiskAssessmentCreate(ai_system_row_id=10), actor_id=1
    )

    assert result.ai_system_row_id == 10
    assert result.sheet_id == 5
    mock_audit.log.assert_called_once()


@patch("app.services.risk_assessment_service.ai_system_inventory_service")
@patch("app.services.risk_assessment_service.sheet_repository")
def test_create_risk_assessment_rejects_missing_ai_system_row(
    mock_sheet_repo, mock_inventory, db
) -> None:
    mock_inventory.get_or_create_sheet.return_value = MagicMock(id=99)
    mock_sheet_repo.get_row.return_value = None

    with pytest.raises(NotFoundError):
        risk_assessment_service.create_risk_assessment(
            db, RiskAssessmentCreate(ai_system_row_id=999), actor_id=1
        )


@patch("app.services.risk_assessment_service.ai_system_inventory_service")
@patch("app.services.risk_assessment_service.sheet_repository")
def test_create_risk_assessment_rejects_row_from_wrong_sheet(
    mock_sheet_repo, mock_inventory, db
) -> None:
    mock_inventory.get_or_create_sheet.return_value = MagicMock(id=99)
    mock_sheet_repo.get_row.return_value = SheetRow(id=10, sheet_id=1, row_index=1, data={})

    with pytest.raises(NotFoundError):
        risk_assessment_service.create_risk_assessment(
            db, RiskAssessmentCreate(ai_system_row_id=10), actor_id=1
        )


@patch("app.services.risk_assessment_service.risk_assessment_repository")
def test_get_risk_assessment_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        risk_assessment_service.get_risk_assessment(db, 999)


@patch("app.services.risk_assessment_service.sheet_service")
@patch("app.services.risk_assessment_service.risk_assessment_repository")
def test_get_sheet_delegates_to_sheet_service(mock_repo, mock_sheet_service, db) -> None:
    risk_assessment = make_risk_assessment(sheet_id=5)
    mock_repo.get.return_value = risk_assessment
    mock_sheet_service.get_sheet.return_value = MagicMock(id=5)

    result = risk_assessment_service.get_sheet(db, 1)

    mock_sheet_service.get_sheet.assert_called_once_with(db, 5)
    assert result.id == 5


@patch("app.services.risk_assessment_service.risk_assessment_repository")
def test_get_sheet_raises_not_found_for_missing_risk_assessment(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        risk_assessment_service.get_sheet(db, 999)


@patch("app.services.risk_assessment_service.audit_service")
@patch("app.services.risk_assessment_service.risk_assessment_repository")
def test_update_risk_assessment(mock_repo, mock_audit, db) -> None:
    risk_assessment = make_risk_assessment()
    mock_repo.get.return_value = risk_assessment
    mock_repo.save.side_effect = lambda _db, ra: ra

    result = risk_assessment_service.update_risk_assessment(
        db, 1, RiskAssessmentUpdate(status=RiskAssessmentStatus.COMPLETED), actor_id=1
    )

    assert result.status == RiskAssessmentStatus.COMPLETED


@patch("app.services.risk_assessment_service.audit_service")
@patch("app.services.risk_assessment_service.framework_service")
@patch("app.services.risk_assessment_service.sheet_repository")
@patch("app.services.risk_assessment_service.risk_assessment_repository")
def test_delete_risk_assessment_also_deletes_its_sheet(
    mock_repo, mock_sheet_repo, mock_framework_service, mock_audit, db
) -> None:
    risk_assessment = make_risk_assessment()
    sheet = MagicMock(id=5)
    mock_repo.get.return_value = risk_assessment
    mock_sheet_repo.get.return_value = sheet

    risk_assessment_service.delete_risk_assessment(db, 1, actor_id=1)

    mock_repo.delete.assert_called_once_with(db, risk_assessment)
    mock_sheet_repo.delete_all_rows.assert_called_once_with(db, 5)
    mock_sheet_repo.delete.assert_called_once_with(db, sheet)


@patch("app.services.risk_assessment_service.sheet_repository")
def test_compute_overall_risk_rating_returns_max_score(mock_sheet_repo, db) -> None:
    mock_sheet_repo.list_rows.return_value = [
        SheetRow(id=1, sheet_id=5, row_index=1, data={"inherent_risk_score": 6}),
        SheetRow(id=2, sheet_id=5, row_index=2, data={"inherent_risk_score": 20}),
        SheetRow(id=3, sheet_id=5, row_index=3, data={"inherent_risk_score": 12}),
    ]

    result = risk_assessment_service.compute_overall_risk_rating(db, 5)

    assert result == 20


@patch("app.services.risk_assessment_service.sheet_repository")
def test_compute_overall_risk_rating_ignores_rows_without_a_score(mock_sheet_repo, db) -> None:
    mock_sheet_repo.list_rows.return_value = [
        SheetRow(id=1, sheet_id=5, row_index=1, data={"category": "Bias"}),
    ]

    result = risk_assessment_service.compute_overall_risk_rating(db, 5)

    assert result is None


@patch("app.services.risk_assessment_service.sheet_repository")
def test_compute_overall_risk_rating_with_no_rows(mock_sheet_repo, db) -> None:
    mock_sheet_repo.list_rows.return_value = []

    result = risk_assessment_service.compute_overall_risk_rating(db, 5)

    assert result is None
