"""AI suggestions of new risk items for a risk assessment.

Every route needs edit rights: a suggestion exists to be added to the sheet,
so asking for one, reading one and applying one are all part of editing it.
Applying goes through risk_assessment_service.add_row -- the same path, and
the same approval withdrawal, as adding a row by hand.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.routers.risk_assessments import _to_read
from app.schemas.risk_assessment import RiskAssessmentRead
from app.schemas.risk_item_suggestion import ApplySuggestionsRequest, RiskSuggestionsRead
from app.services import risk_item_suggestion_service as suggestions

router = APIRouter(prefix="/risk-assessments", tags=["risk-assessments"])


@router.post(
    "/{risk_assessment_id}/ai-risk-suggestions", response_model=RiskSuggestionsRead, status_code=201
)
def generate_suggestions(
    risk_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskSuggestionsRead:
    return suggestions.generate_suggestions(db, risk_assessment_id, actor_id)


@router.get(
    "/{risk_assessment_id}/ai-risk-suggestions/latest", response_model=RiskSuggestionsRead | None
)
def latest_suggestions(
    risk_assessment_id: int,
    db: Session = Depends(get_db),
    _actor_id: int | None = Depends(get_current_actor_id),
) -> RiskSuggestionsRead | None:
    """The suggestions still waiting for a decision, if there are any."""
    return suggestions.latest_suggestions(db, risk_assessment_id)


@router.post(
    "/{risk_assessment_id}/ai-risk-suggestions/{draft_id}/apply", response_model=RiskAssessmentRead
)
def apply_suggestions(
    risk_assessment_id: int,
    draft_id: int,
    data: ApplySuggestionsRequest,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskAssessmentRead:
    risk_assessment = suggestions.apply_suggestions(
        db,
        risk_assessment_id,
        draft_id,
        [
            suggestions.AcceptedItem(
                key=item.key,
                category=item.category,
                description=item.description,
                mitigation=item.mitigation,
                likelihood=item.likelihood,
                impact=item.impact,
                risk_owner=item.risk_owner,
            )
            for item in data.accepted
        ],
        actor_id,
    )
    return _to_read(db, risk_assessment)


@router.post("/{risk_assessment_id}/ai-risk-suggestions/{draft_id}/discard", status_code=204)
def discard_suggestions(
    risk_assessment_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> Response:
    suggestions.discard_suggestions(db, risk_assessment_id, draft_id, actor_id)
    return Response(status_code=204)
