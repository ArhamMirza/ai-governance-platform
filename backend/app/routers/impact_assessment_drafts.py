"""AI drafts of a whole impact assessment.

Every route needs edit rights: a draft exists to be written into the record,
so asking for one, reading one and applying one are all part of editing it.
Applying goes through the same service functions -- and the same approval
withdrawal -- as saving a field by hand.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.routers.impact_assessments import _to_read
from app.schemas.ai_draft import AiDraftRead, ApplyDraftRequest, GenerateDraftRequest
from app.schemas.impact_assessment import ImpactAssessmentRead
from app.services import impact_assessment_drafting_service as drafting

router = APIRouter(prefix="/impact-assessments", tags=["impact-assessments"])


@router.post("/{impact_assessment_id}/ai-drafts", response_model=AiDraftRead, status_code=201)
def generate_draft(
    impact_assessment_id: int,
    data: GenerateDraftRequest | None = None,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AiDraftRead:
    return drafting.generate_draft(
        db, impact_assessment_id, actor_id, data.instructions if data else None
    )


@router.get("/{impact_assessment_id}/ai-drafts/latest", response_model=AiDraftRead | None)
def latest_draft(
    impact_assessment_id: int,
    db: Session = Depends(get_db),
    _actor_id: int | None = Depends(get_current_actor_id),
) -> AiDraftRead | None:
    """The draft still waiting for a decision, if there is one."""
    return drafting.latest_draft(db, impact_assessment_id)


@router.post(
    "/{impact_assessment_id}/ai-drafts/{draft_id}/apply", response_model=ImpactAssessmentRead
)
def apply_draft(
    impact_assessment_id: int,
    draft_id: int,
    data: ApplyDraftRequest,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImpactAssessmentRead:
    assessment = drafting.apply_draft(
        db,
        impact_assessment_id,
        draft_id,
        [drafting.Decision(key=f.key, value=f.value) for f in data.accepted],
        actor_id,
    )
    return _to_read(db, assessment)


@router.post("/{impact_assessment_id}/ai-drafts/{draft_id}/discard", status_code=204)
def discard_draft(
    impact_assessment_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> Response:
    drafting.discard_draft(db, impact_assessment_id, draft_id, actor_id)
    return Response(status_code=204)
