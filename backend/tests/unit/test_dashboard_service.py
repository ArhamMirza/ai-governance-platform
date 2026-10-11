import inspect
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.core import risk_scoring
from app.models.ai_incident import AIIncident
from app.models.audit_program import AuditProgram
from app.models.competence_requirement import CompetenceRequirement
from app.models.corrective_action import CorrectiveAction
from app.models.management_review_settings import ManagementReviewSettings
from app.models.policy import Policy, PolicyStatus
from app.models.procedure import Procedure, ProcedureStatus
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.sheet import SheetRow
from app.models.supplier import Supplier
from app.schemas.competence import PersonCompetence
from app.services import dashboard_service

PAST_DEADLINE = "2020-01-01"
FUTURE_DEADLINE = "2099-01-01"
PAST_DATE = date(2020, 1, 1)
FUTURE_DATE = date(2099, 1, 1)


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


def make_corrective_action(**overrides) -> CorrectiveAction:
    defaults = dict(
        id=1,
        title="Fix drift",
        nonconformity_description="x",
        root_cause=None,
        action_description=None,
        source_type=None,
        source_id=None,
        assignee_id=None,
        due_date=FUTURE_DATE,
        status="open",
        closed_by=None,
        closed_at=None,
    )
    defaults.update(overrides)
    return CorrectiveAction(**defaults)


def make_audit_program(**overrides) -> AuditProgram:
    defaults = dict(
        id=1,
        title="Audit Program",
        description=None,
        schedule_type="interval",
        interval_months=6,
        start_date=FUTURE_DATE,
        owner_id=None,
        status="active",
    )
    defaults.update(overrides)
    return AuditProgram(**defaults)


def make_management_review_settings(**overrides) -> ManagementReviewSettings:
    defaults = dict(id=1, interval_months=12, start_date=FUTURE_DATE)
    defaults.update(overrides)
    return ManagementReviewSettings(**defaults)


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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_counts_by_status(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_counts_high_risk_assessments(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_uses_configured_bands(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    """A score of 8 is medium by default but high once the org lowers the band."""
    mock_criteria.get_bands.return_value = risk_scoring.Bands(medium_min_score=4, high_min_score=8)
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_reports_risk_items_and_coverage(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_attention_lists_only_nonzero_items(
    mock_mr_repo,
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
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_handles_empty_data(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
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
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_my_risk_items_matches_owner_and_excludes_closed(
    mock_mr_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = [make_risk_assessment(id=1, sheet_id=1)]
    mock_sheet_repo.list_rows_for_sheets.return_value = {
        1: [
            # Owned by me, overdue and open -- should appear.
            make_risk_row(
                4,
                4,
                id=1,
                sheet_id=1,
                risk_owner="99",
                treatment_deadline=PAST_DEADLINE,
                status="open",
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


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.corrective_action_repository")
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_my_corrective_actions_matches_assignee_and_flags_overdue(
    mock_mr_repo,
    mock_ca_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = []
    mock_sheet_repo.list_rows_for_sheets.return_value = {}
    mock_ca_repo.list_all.return_value = [
        # Assigned to me, overdue and still open -- should appear, flagged.
        make_corrective_action(id=1, assignee_id=99, due_date=PAST_DATE, status="open"),
        # Assigned to me but already closed -- should be excluded.
        make_corrective_action(id=2, assignee_id=99, due_date=PAST_DATE, status="closed"),
        # Assigned to someone else -- should be excluded.
        make_corrective_action(id=3, assignee_id=1, due_date=PAST_DATE, status="open"),
        # Assigned to me, not yet due -- should appear, not flagged.
        make_corrective_action(id=4, assignee_id=99, due_date=FUTURE_DATE, status="in_progress"),
    ]

    result = dashboard_service.get_summary(db, actor_id=99)

    assert [item.id for item in result.my_corrective_actions] == [1, 4]
    assert result.my_corrective_actions[0].overdue is True
    assert result.my_corrective_actions[1].overdue is False
    assert any(item.key == "overdue_corrective_actions" for item in result.attention)


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.internal_audit_repository")
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_flags_overdue_internal_audit_programs(
    mock_mr_repo,
    mock_ia_repo,
    mock_policy_repo,
    mock_procedure_repo,
    mock_inventory,
    mock_ra_repo,
    mock_sheet_repo,
    mock_criteria,
    db,
) -> None:
    mock_criteria.get_bands.return_value = risk_scoring.DEFAULT_BANDS
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    mock_policy_repo.list_all.return_value = []
    mock_procedure_repo.list_all.return_value = []
    mock_inventory.list_rows.return_value = []
    mock_ra_repo.list_all.return_value = []
    mock_sheet_repo.list_rows_for_sheets.return_value = {}
    overdue_program = make_audit_program(id=1, schedule_type="interval", start_date=PAST_DATE)
    current_program = make_audit_program(id=2, schedule_type="interval", start_date=FUTURE_DATE)
    mock_ia_repo.list_programs.return_value = [overdue_program, current_program]
    mock_ia_repo.list_for_program.return_value = []

    result = dashboard_service.get_summary(db, actor_id=99)

    assert any(item.key == "audits_overdue" and item.count == 1 for item in result.attention)


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.internal_audit_repository")
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_flags_an_overdue_management_review(
    mock_mr_repo,
    mock_ia_repo,
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
    mock_ia_repo.list_programs.return_value = []
    mock_mr_repo.get_settings.return_value = make_management_review_settings(start_date=PAST_DATE)
    mock_mr_repo.list_meetings.return_value = []

    result = dashboard_service.get_summary(db, actor_id=99)

    assert any(
        item.key == "management_review_overdue" and item.count == 1 for item in result.attention
    )


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.internal_audit_repository")
@patch("app.services.dashboard_service.management_review_repository")
def test_get_summary_hides_management_review_when_not_overdue(
    mock_mr_repo,
    mock_ia_repo,
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
    mock_ia_repo.list_programs.return_value = []
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []

    result = dashboard_service.get_summary(db, actor_id=99)

    assert not any(item.key == "management_review_overdue" for item in result.attention)


def make_incident(**overrides) -> AIIncident:
    defaults = dict(
        id=1,
        title="Harmful output",
        description="x",
        detected_on=PAST_DATE,
        status="open",
        is_serious=False,
        serious_category=None,
        authority_notified_on=None,
    )
    defaults.update(overrides)
    return AIIncident(**defaults)


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.management_review_repository")
@patch("app.services.dashboard_service.ai_incident_repository")
def test_get_summary_flags_open_incidents_and_overdue_serious_reports(
    mock_incident_repo,
    mock_mr_repo,
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
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    mock_incident_repo.list_all.return_value = [
        # Serious, never reported, deadline long gone.
        make_incident(id=1, is_serious=True, serious_category="death"),
        # Serious but reported -- open, not overdue.
        make_incident(
            id=2, is_serious=True, serious_category="death", authority_notified_on=PAST_DATE
        ),
        # Resolved -- neither.
        make_incident(id=3, status="resolved"),
    ]

    result = dashboard_service.get_summary(db, actor_id=99)

    counts = {item.key: item.count for item in result.attention}
    assert counts["incident_reports_overdue"] == 1
    assert counts["open_incidents"] == 2


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.management_review_repository")
@patch("app.services.dashboard_service.competence_service")
def test_get_summary_counts_competence_gaps_and_lists_my_training(
    mock_competence,
    mock_mr_repo,
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
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    awareness = CompetenceRequirement(id=1, title="AI policy awareness")
    bias = CompetenceRequirement(id=2, title="Bias testing")
    mock_competence.standings.return_value = [
        (
            awareness,
            [
                PersonCompetence(
                    user_id=99, status="current", last_completed_on=PAST_DATE, next_due=None
                ),
                PersonCompetence(
                    user_id=5, status="missing", last_completed_on=None, next_due=None
                ),
            ],
        ),
        (
            bias,
            [
                PersonCompetence(
                    user_id=99, status="expired", last_completed_on=PAST_DATE, next_due=PAST_DATE
                ),
            ],
        ),
    ]
    mock_competence.gap_count.side_effect = lambda people: sum(
        1 for person in people if person.status != "current"
    )

    result = dashboard_service.get_summary(db, actor_id=99)

    counts = {item.key: item.count for item in result.attention}
    assert counts["competence_gaps"] == 2
    assert [(item.title, item.status) for item in result.my_training] == [
        ("Bias testing", "expired")
    ]


@patch("app.services.dashboard_service.risk_criteria_service")
@patch("app.services.dashboard_service.sheet_repository")
@patch("app.services.dashboard_service.risk_assessment_repository")
@patch("app.services.dashboard_service.ai_system_inventory_service")
@patch("app.services.dashboard_service.procedure_repository")
@patch("app.services.dashboard_service.policy_repository")
@patch("app.services.dashboard_service.management_review_repository")
@patch("app.services.dashboard_service.supplier_repository")
def test_get_summary_flags_supplier_reviews_and_contracts(
    mock_supplier_repo,
    mock_mr_repo,
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
    mock_mr_repo.get_settings.return_value = None
    mock_mr_repo.list_meetings.return_value = []
    mock_supplier_repo.list_reviews.return_value = []
    mock_supplier_repo.list_all.return_value = [
        # Review long overdue, contract long ended.
        Supplier(
            id=1,
            name="Overdue Co",
            status="active",
            review_interval_months=12,
            first_review_due=PAST_DATE,
            contract_end=PAST_DATE,
        ),
        # Nothing due.
        Supplier(id=2, name="Fine Co", status="active", contract_end=FUTURE_DATE),
        # Inactive -- never alerts.
        Supplier(
            id=3,
            name="Former Co",
            status="inactive",
            review_interval_months=12,
            first_review_due=PAST_DATE,
            contract_end=PAST_DATE,
        ),
    ]

    result = dashboard_service.get_summary(db, actor_id=99)

    counts = {item.key: item.count for item in result.attention}
    assert counts["supplier_reviews_overdue"] == 1
    assert counts["supplier_contracts_expiring"] == 1


ATTENTION_PARAMS = list(inspect.signature(dashboard_service._attention).parameters)


def _attention_with(**counts):
    """_attention with every count zero except the ones given."""
    defaults = {name: 0 for name in ATTENTION_PARAMS}
    defaults["management_review_overdue"] = False
    return dashboard_service._attention(**{**defaults, **counts})


def test_every_attention_item_belongs_to_a_known_area() -> None:
    items = _attention_with(
        **{**{name: 1 for name in ATTENTION_PARAMS}, "management_review_overdue": True}
    )

    assert len(items) == 27
    assert {item.group for item in items} == set(dashboard_service.ATTENTION_GROUP_ORDER)


def test_attention_items_are_contiguous_by_area() -> None:
    # _attention lists these interleaved: an inventory item, a risk item,
    # then another inventory item.
    items = _attention_with(
        retention_expired_count=1,
        unassessed_count=1,
        ai_systems_without_owner_count=1,
    )

    groups = [item.group for item in items]
    runs = [group for i, group in enumerate(groups) if i == 0 or groups[i - 1] != group]
    assert len(runs) == len(set(groups))


def test_areas_with_something_critical_come_first() -> None:
    items = _attention_with(
        competence_gap_count=3,  # People -- warning only
        supplier_reviews_overdue_count=1,  # Inventory -- critical
        open_incident_count=2,  # Incidents -- warning only
    )

    assert [item.group for item in items] == [
        dashboard_service.INVENTORY_GROUP,
        dashboard_service.INCIDENTS_GROUP,
        dashboard_service.PEOPLE_GROUP,
    ]


def test_within_an_area_critical_items_come_before_warnings() -> None:
    # _attention lists the (warning) retention item before the (critical)
    # supplier review item; the panel should flip them.
    items = _attention_with(retention_expired_count=1, supplier_reviews_overdue_count=1)

    assert [item.key for item in items] == ["supplier_reviews_overdue", "retention_expired"]


def test_objective_items_sit_in_their_own_area_after_risk() -> None:
    items = _attention_with(
        objectives_falling_short_count=2,
        objective_measurements_overdue_count=1,
        overdue_count=1,  # Risk -- critical, so its area leads
        open_incident_count=1,  # Incidents -- warning only
    )

    assert [(item.key, item.count) for item in items] == [
        ("overdue_treatments", 1),
        ("open_incidents", 1),
        ("objectives_off_track", 2),
        ("objective_measurements_overdue", 1),
    ]
    assert {item.group for item in items if item.key.startswith("objective")} == {
        dashboard_service.OBJECTIVES_GROUP
    }
