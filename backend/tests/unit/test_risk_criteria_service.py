import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.risk_criteria import DEFAULT_HIGH_MIN_SCORE, DEFAULT_MEDIUM_MIN_SCORE
from app.schemas.risk_criteria import RiskCriteriaUpdate
from app.services import risk_criteria_service


def test_defaults_are_returned_before_anything_is_saved(db_session: Session) -> None:
    criteria = risk_criteria_service.get_criteria(db_session)

    assert criteria.medium_min_score == DEFAULT_MEDIUM_MIN_SCORE
    assert criteria.high_min_score == DEFAULT_HIGH_MIN_SCORE
    assert criteria.is_default is True
    assert criteria.updated_at is None


def test_reading_defaults_does_not_persist_a_row(db_session: Session) -> None:
    risk_criteria_service.get_criteria(db_session)

    assert risk_criteria_service.get_criteria(db_session).is_default is True


def test_update_persists_and_clears_default_flag(db_session: Session) -> None:
    result = risk_criteria_service.update_criteria(
        db_session, RiskCriteriaUpdate(medium_min_score=4, high_min_score=10), None
    )

    assert result.medium_min_score == 4
    assert result.high_min_score == 10
    assert result.is_default is False
    assert risk_criteria_service.get_criteria(db_session).high_min_score == 10


def test_update_twice_reuses_the_single_row(db_session: Session) -> None:
    risk_criteria_service.update_criteria(
        db_session, RiskCriteriaUpdate(medium_min_score=4, high_min_score=10), None
    )
    risk_criteria_service.update_criteria(
        db_session, RiskCriteriaUpdate(medium_min_score=6, high_min_score=15), None
    )

    criteria = risk_criteria_service.get_criteria(db_session)
    assert criteria.medium_min_score == 6
    assert criteria.high_min_score == 15


def test_get_bands_reflects_saved_criteria(db_session: Session) -> None:
    risk_criteria_service.update_criteria(
        db_session, RiskCriteriaUpdate(medium_min_score=3, high_min_score=9), None
    )

    bands = risk_criteria_service.get_bands(db_session)

    assert bands.medium_min_score == 3
    assert bands.high_min_score == 9


def test_reset_restores_defaults(db_session: Session) -> None:
    risk_criteria_service.update_criteria(
        db_session, RiskCriteriaUpdate(medium_min_score=3, high_min_score=9), None
    )

    result = risk_criteria_service.reset_criteria(db_session, None)

    assert result.medium_min_score == DEFAULT_MEDIUM_MIN_SCORE
    assert result.high_min_score == DEFAULT_HIGH_MIN_SCORE
    # Value-based, so a reset reads as defaults again even though a row exists.
    assert result.is_default is True
    assert result.updated_at is not None


@pytest.mark.parametrize(
    ("medium", "high"),
    [
        (10, 10),  # bands must not collide
        (12, 8),  # medium above high
        (1, 10),  # medium at the floor leaves no low band
        (5, 26),  # high beyond the 5x5 maximum
        (0, 10),
    ],
)
def test_invalid_bands_are_rejected(db_session: Session, medium: int, high: int) -> None:
    with pytest.raises(ValidationError):
        risk_criteria_service.update_criteria(
            db_session, RiskCriteriaUpdate(medium_min_score=medium, high_min_score=high), None
        )
