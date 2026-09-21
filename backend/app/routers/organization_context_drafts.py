"""AI drafts of the organization's ISO/IEC 42001 Clause 4 context.

Every route needs edit rights: a draft exists to be written into the
record, so asking for one, reading one and applying one are all part of
editing it. Applying goes through organization_context_service's own
functions -- the same path, and the same approval withdrawal, as editing
the narrative or a row by hand.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.ai_draft import GenerateDraftRequest
from app.schemas.organization_context import OrganizationContextRead
from app.schemas.organization_context_draft import (
    ApplyOrganizationContextDraftRequest,
    OrganizationContextDraftRead,
)
from app.services import organization_context_drafting_service as drafting

router = APIRouter(prefix="/organization-context/ai-draft", tags=["organization-context"])


@router.post("", response_model=OrganizationContextDraftRead, status_code=201)
def generate_draft(
    data: GenerateDraftRequest | None = None,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> OrganizationContextDraftRead:
    return drafting.generate_draft(db, actor_id, data.instructions if data else None)


@router.get("/latest", response_model=OrganizationContextDraftRead | None)
def latest_draft(
    db: Session = Depends(get_db),
    _actor_id: int | None = Depends(get_current_actor_id),
) -> OrganizationContextDraftRead | None:
    """The draft still waiting for a decision, if there is one."""
    return drafting.latest_draft(db)


@router.post("/{draft_id}/apply", response_model=OrganizationContextRead)
def apply_draft(
    draft_id: int,
    data: ApplyOrganizationContextDraftRequest,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> OrganizationContextRead:
    return drafting.apply_draft(
        db,
        draft_id,
        [
            drafting.AcceptedNarrative(key=item.key, value=item.value)
            for item in data.narrative
        ],
        [
            drafting.AcceptedIssue(
                key=item.key,
                category=item.category,
                issue=item.issue,
                planned_response=item.planned_response,
            )
            for item in data.issues
        ],
        [
            drafting.AcceptedParty(
                key=item.key,
                party=item.party,
                needs=item.needs,
                expectations=item.expectations,
                requirements=item.requirements,
            )
            for item in data.interested_parties
        ],
        actor_id,
    )


@router.post("/{draft_id}/discard", status_code=204)
def discard_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> Response:
    drafting.discard_draft(db, draft_id, actor_id)
    return Response(status_code=204)
