from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.ai_use import BuiltinDetectorRead, DLPRuleCreate, DLPRuleRead, DLPRuleUpdate
from app.services import dlp_rule_service

router = APIRouter(prefix="/dlp-rules", tags=["dlp-rules"])


@router.get("", response_model=list[DLPRuleRead])
def list_rules(db: Session = Depends(get_db)) -> list[DLPRuleRead]:
    return [DLPRuleRead.model_validate(r) for r in dlp_rule_service.list_rules(db)]


# Declared before the /{rule_id} routes, so "detectors" isn't taken for an id.
@router.get("/detectors", response_model=list[BuiltinDetectorRead])
def list_detectors() -> list[BuiltinDetectorRead]:
    return [
        BuiltinDetectorRead(key=key, label=label, description=text)
        for key, label, text in dlp_rule_service.builtin_detectors()
    ]


@router.post("", response_model=DLPRuleRead, status_code=201)
def create_rule(
    data: DLPRuleCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> DLPRuleRead:
    return DLPRuleRead.model_validate(dlp_rule_service.create_rule(db, data, actor_id))


@router.get("/{rule_id}", response_model=DLPRuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)) -> DLPRuleRead:
    return DLPRuleRead.model_validate(dlp_rule_service.get_rule(db, rule_id))


@router.put("/{rule_id}", response_model=DLPRuleRead)
def update_rule(
    rule_id: int,
    data: DLPRuleUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> DLPRuleRead:
    return DLPRuleRead.model_validate(dlp_rule_service.update_rule(db, rule_id, data, actor_id))


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    dlp_rule_service.delete_rule(db, rule_id, actor_id)
