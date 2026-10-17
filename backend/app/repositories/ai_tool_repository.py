from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_tool import AITool, AIToolRequest, AIToolRequestStatus


def get(db: Session, tool_id: int) -> AITool | None:
    return db.get(AITool, tool_id)


def list_all(db: Session) -> list[AITool]:
    return list(db.scalars(select(AITool).order_by(AITool.name, AITool.id)))


def create(db: Session, tool: AITool) -> AITool:
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def save(db: Session, tool: AITool) -> AITool:
    db.commit()
    db.refresh(tool)
    return tool


def delete(db: Session, tool: AITool) -> None:
    db.delete(tool)
    db.commit()


def get_request(db: Session, request_id: int) -> AIToolRequest | None:
    return db.get(AIToolRequest, request_id)


def list_requests(db: Session) -> list[AIToolRequest]:
    return list(
        db.scalars(
            select(AIToolRequest).order_by(
                AIToolRequest.requested_on.desc(), AIToolRequest.id.desc()
            )
        )
    )


def list_requests_for_requester(db: Session, requester_id: int) -> list[AIToolRequest]:
    return list(
        db.scalars(
            select(AIToolRequest)
            .where(AIToolRequest.requester_id == requester_id)
            .order_by(AIToolRequest.requested_on.desc(), AIToolRequest.id.desc())
        )
    )


def list_open_requests(db: Session) -> list[AIToolRequest]:
    return list(
        db.scalars(
            select(AIToolRequest)
            .where(AIToolRequest.status == AIToolRequestStatus.REQUESTED)
            .order_by(AIToolRequest.requested_on, AIToolRequest.id)
        )
    )


def create_request(db: Session, request: AIToolRequest) -> AIToolRequest:
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def save_request(db: Session, request: AIToolRequest) -> AIToolRequest:
    db.commit()
    db.refresh(request)
    return request


def list_requests_for_tool(db: Session, tool_id: int) -> list[AIToolRequest]:
    return list(
        db.scalars(
            select(AIToolRequest).where(AIToolRequest.tool_id == tool_id).order_by(AIToolRequest.id)
        )
    )
