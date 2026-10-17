"""What the browser extension talks to.

Not part of the signed-in app: the extension has no session, it presents the
organization's enrollment key (app.core.agent_key). That key lets it do two
things and nothing else -- read the policy, and send usage counts -- so every
route here takes require_agent_key and none touches the rest of the platform.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_agent_key
from app.schemas.ai_use import AgentEvents, AgentEventsAccepted, AgentPolicy
from app.services import ai_usage_service

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(require_agent_key)])


@router.get("/policy", response_model=AgentPolicy)
def get_policy(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> AgentPolicy | Response:
    """The tools, rules and settings to apply. Answers 304 when the caller
    already has this exact policy (If-None-Match), so polling is cheap."""
    policy = ai_usage_service.build_policy(db)
    etag = ai_usage_service.policy_etag(policy)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return policy


@router.post("/events", response_model=AgentEventsAccepted, status_code=202)
def post_events(data: AgentEvents, db: Session = Depends(get_db)) -> AgentEventsAccepted:
    return AgentEventsAccepted(accepted=ai_usage_service.record_events(db, data))
