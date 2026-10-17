from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.models.ai_tool import AITool, AIToolRequest
from app.schemas.ai_tool import (
    AIToolCreate,
    AIToolDecision,
    AIToolRead,
    AIToolRequestDecision,
    AIToolRequestRead,
    AIToolStandingRead,
    AIToolUpdate,
)
from app.services import ai_tool_service, framework_service

router = APIRouter(prefix="/ai-tools", tags=["ai-tools"])


def _to_read(db: Session, tool: AITool) -> AIToolRead:
    return AIToolRead(
        id=tool.id,
        name=tool.name,
        vendor=tool.vendor,
        domains=tool.domains,
        description=tool.description,
        status=tool.status,
        max_data_classification=tool.max_data_classification,
        conditions_of_use=tool.conditions_of_use,
        owner_id=tool.owner_id,
        supplier_id=tool.supplier_id,
        decided_by=tool.decided_by,
        decided_on=tool.decided_on,
        decision_note=tool.decision_note,
        review_due=tool.review_due,
        standing=AIToolStandingRead(review_overdue=ai_tool_service.review_overdue(tool)),
        framework_tags=framework_service.get_tags(db, ai_tool_service.ENTITY_TYPE, tool.id),
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


def _request_read(request: AIToolRequest) -> AIToolRequestRead:
    return AIToolRequestRead.model_validate(request, from_attributes=True)


@router.get("", response_model=list[AIToolRead])
def list_tools(db: Session = Depends(get_db)) -> list[AIToolRead]:
    return [_to_read(db, tool) for tool in ai_tool_service.list_tools(db)]


@router.post("", response_model=AIToolRead, status_code=201)
def create_tool(
    data: AIToolCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AIToolRead:
    return _to_read(db, ai_tool_service.create_tool(db, data, actor_id))


# Declared before the /{tool_id} routes, so "requests" isn't taken for an id.
@router.get("/requests", response_model=list[AIToolRequestRead])
def list_requests(db: Session = Depends(get_db)) -> list[AIToolRequestRead]:
    return [_request_read(request) for request in ai_tool_service.list_requests(db)]


@router.get("/requests/{request_id}", response_model=AIToolRequestRead)
def get_request(request_id: int, db: Session = Depends(get_db)) -> AIToolRequestRead:
    return _request_read(ai_tool_service.get_request(db, request_id))


@router.post("/requests/{request_id}/decision", response_model=AIToolRequestRead)
def decide_request(
    request_id: int,
    data: AIToolRequestDecision,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> AIToolRequestRead:
    return _request_read(ai_tool_service.decide_request(db, request_id, data, actor_id))


@router.get("/{tool_id}", response_model=AIToolRead)
def get_tool(tool_id: int, db: Session = Depends(get_db)) -> AIToolRead:
    return _to_read(db, ai_tool_service.get_tool(db, tool_id))


@router.put("/{tool_id}", response_model=AIToolRead)
def update_tool(
    tool_id: int,
    data: AIToolUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AIToolRead:
    return _to_read(db, ai_tool_service.update_tool(db, tool_id, data, actor_id))


@router.delete("/{tool_id}", status_code=204)
def delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    ai_tool_service.delete_tool(db, tool_id, actor_id)


@router.post("/{tool_id}/decision", response_model=AIToolRead)
def decide_tool(
    tool_id: int,
    data: AIToolDecision,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> AIToolRead:
    return _to_read(db, ai_tool_service.decide_tool(db, tool_id, data, actor_id))
