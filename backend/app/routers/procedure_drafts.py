"""AI drafts of a Procedure's title and description.

Every route needs edit rights: a draft exists to be written into the
record, so asking for one, reading one and applying one are all part of
editing it. Applying goes through procedure_service.update_procedure --
the same path, and the same draft-only edit rule, as saving a field by
hand.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.ai_draft import AiDraftRead, ApplyDraftRequest, GenerateDraftRequest
from app.schemas.procedure import ProcedureRead
from app.services import procedure_drafting_service as drafting

router = APIRouter(prefix="/procedures", tags=["procedures"])


@router.post("/{procedure_id}/ai-draft", response_model=AiDraftRead, status_code=201)
def generate_draft(
    procedure_id: int,
    data: GenerateDraftRequest | None = None,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AiDraftRead:
    return drafting.generate_draft(
        db, procedure_id, actor_id, data.instructions if data else None
    )


@router.get("/{procedure_id}/ai-draft/latest", response_model=AiDraftRead | None)
def latest_draft(
    procedure_id: int,
    db: Session = Depends(get_db),
    _actor_id: int | None = Depends(get_current_actor_id),
) -> AiDraftRead | None:
    """The draft still waiting for a decision, if there is one."""
    return drafting.latest_draft(db, procedure_id)


@router.post("/{procedure_id}/ai-draft/{draft_id}/apply", response_model=ProcedureRead)
def apply_draft(
    procedure_id: int,
    draft_id: int,
    data: ApplyDraftRequest,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ProcedureRead:
    return drafting.apply_draft(
        db,
        procedure_id,
        draft_id,
        [drafting.Decision(key=f.key, value=f.value) for f in data.accepted],
        actor_id,
    )


@router.post("/{procedure_id}/ai-draft/{draft_id}/discard", status_code=204)
def discard_draft(
    procedure_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> Response:
    drafting.discard_draft(db, procedure_id, draft_id, actor_id)
    return Response(status_code=204)
