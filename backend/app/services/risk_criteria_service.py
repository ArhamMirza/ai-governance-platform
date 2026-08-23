"""Organization-configurable risk appetite.

The criteria are a singleton: until someone saves their own, every read falls
back to the documented defaults rather than writing a row on first access.
"""

from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.core.exceptions import ValidationError
from app.models.risk_criteria import (
    DEFAULT_HIGH_MIN_SCORE,
    DEFAULT_MEDIUM_MIN_SCORE,
    MAX_SCORE,
    MIN_SCORE,
    RiskCriteria,
)
from app.repositories import risk_criteria_repository
from app.schemas.risk_criteria import RiskCriteriaRead, RiskCriteriaUpdate
from app.services import audit_service

ENTITY_TYPE = "RiskCriteria"

# The singleton row's audit entity id -- there is only ever one.
ENTITY_ID = 1


def _validate(medium_min_score: int, high_min_score: int) -> None:
    if not MIN_SCORE < medium_min_score <= MAX_SCORE:
        raise ValidationError(
            f"medium_min_score must be between {MIN_SCORE + 1} and {MAX_SCORE}"
        )
    if not MIN_SCORE < high_min_score <= MAX_SCORE:
        raise ValidationError(
            f"high_min_score must be between {MIN_SCORE + 1} and {MAX_SCORE}"
        )
    if medium_min_score >= high_min_score:
        raise ValidationError("medium_min_score must be lower than high_min_score")


def get_criteria(db: Session) -> RiskCriteriaRead:
    criteria = risk_criteria_repository.get(db)
    if criteria is None:
        return RiskCriteriaRead(
            medium_min_score=DEFAULT_MEDIUM_MIN_SCORE,
            high_min_score=DEFAULT_HIGH_MIN_SCORE,
            is_default=True,
            min_score=MIN_SCORE,
            max_score=MAX_SCORE,
            updated_at=None,
        )
    return RiskCriteriaRead(
        medium_min_score=criteria.medium_min_score,
        high_min_score=criteria.high_min_score,
        # Value-based, so a reset reads as "using defaults" again.
        is_default=(
            criteria.medium_min_score == DEFAULT_MEDIUM_MIN_SCORE
            and criteria.high_min_score == DEFAULT_HIGH_MIN_SCORE
        ),
        min_score=MIN_SCORE,
        max_score=MAX_SCORE,
        updated_at=criteria.updated_at,
    )


def get_bands(db: Session) -> risk_scoring.Bands:
    """The bands every aggregation should score against."""
    criteria = get_criteria(db)
    return risk_scoring.Bands(
        medium_min_score=criteria.medium_min_score,
        high_min_score=criteria.high_min_score,
    )


def update_criteria(
    db: Session, data: RiskCriteriaUpdate, actor_id: int | None
) -> RiskCriteriaRead:
    _validate(data.medium_min_score, data.high_min_score)

    criteria = risk_criteria_repository.get(db)
    if criteria is None:
        criteria = risk_criteria_repository.create(
            db,
            RiskCriteria(
                medium_min_score=data.medium_min_score,
                high_min_score=data.high_min_score,
            ),
        )
    else:
        criteria.medium_min_score = data.medium_min_score
        criteria.high_min_score = data.high_min_score
        criteria = risk_criteria_repository.save(db, criteria)

    audit_service.log(
        db,
        ENTITY_TYPE,
        ENTITY_ID,
        "updated",
        actor_id,
        {
            "medium_min_score": data.medium_min_score,
            "high_min_score": data.high_min_score,
        },
    )
    return get_criteria(db)


def reset_criteria(db: Session, actor_id: int | None) -> RiskCriteriaRead:
    """Return to the built-in defaults."""
    return update_criteria(
        db,
        RiskCriteriaUpdate(
            medium_min_score=DEFAULT_MEDIUM_MIN_SCORE,
            high_min_score=DEFAULT_HIGH_MIN_SCORE,
        ),
        actor_id,
    )
