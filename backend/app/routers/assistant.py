"""The chat assistant's API.

Open to any signed-in user rather than only editors: the assistant reads
and answers, it changes nothing, and the people with the most questions
about a governance record are often the ones who can only view it -- an
auditor, a reviewer, a new system owner. Cost is bounded by the per-person
daily token budget, not by role.

Every route works on the signed-in user's own conversations and no one
else's. There is no admin view of other people's chats.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core import embeddings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.assistant import (
    AskRequest,
    ConversationDetail,
    ConversationRead,
    ConversationStart,
    MessageRead,
)
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/warm", status_code=202)
def warm(background: BackgroundTasks, _user: User = Depends(get_current_user)) -> dict:
    """Start loading the models in the background, before anyone asks.

    Called when the assistant first appears in a browser. A fresh server
    otherwise spends its first several seconds loading the embedding model
    and the model client -- on the first question someone asks.
    """
    background.add_task(embeddings.warm)
    return {"status": "warming"}


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ConversationRead]:
    return assistant_service.list_conversations(db, user.id)


@router.post("/conversations", response_model=ConversationRead, status_code=201)
def start_conversation(
    data: ConversationStart,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversationRead:
    return assistant_service.start_conversation(
        db, user.id, data.context_entity_type, data.context_entity_id
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversationDetail:
    conversation = assistant_service.get_conversation(db, user.id, conversation_id)
    messages = assistant_service.messages_of(db, user.id, conversation_id)
    return ConversationDetail(
        **ConversationRead.model_validate(conversation).model_dump(),
        messages=[MessageRead.model_validate(m) for m in messages],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
def ask(
    conversation_id: int,
    data: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageRead:
    return assistant_service.ask(db, user.id, conversation_id, data.question)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    assistant_service.delete_conversation(db, user.id, conversation_id)
