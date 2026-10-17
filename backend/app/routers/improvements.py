from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.improvement_tracking import ImprovementStanding
from app.dependencies import get_current_actor_id
from app.models.improvement import Improvement
from app.schemas.improvement import (
    ImprovementAsOfRead,
    ImprovementCreate,
    ImprovementRead,
    ImprovementStandingRead,
    ImprovementStatusUpdate,
    ImprovementUpdate,
)
from app.services import framework_service, improvement_service

router = APIRouter(prefix="/improvements", tags=["improvements"])


def _standing_read(standing: ImprovementStanding) -> ImprovementStandingRead:
    return ImprovementStandingRead(state=standing.state, overdue=standing.overdue)


def _to_read(db: Session, improvement: Improvement) -> ImprovementRead:
    return ImprovementRead(
        id=improvement.id,
        title=improvement.title,
        description=improvement.description,
        expected_benefit=improvement.expected_benefit,
        source=improvement.source,
        source_type=improvement.source_type,
        source_id=improvement.source_id,
        source_label=improvement_service.source_label(db, improvement),
        owner_id=improvement.owner_id,
        raised_on=improvement.raised_on,
        target_date=improvement.target_date,
        status=improvement.status,
        decided_on=improvement.decided_on,
        closed_on=improvement.closed_on,
        outcome=improvement.outcome,
        decline_reason=improvement.decline_reason,
        change_id=improvement.change_id,
        standing=_standing_read(improvement_service.standing(improvement)),
        framework_tags=framework_service.get_tags(
            db, improvement_service.ENTITY_TYPE, improvement.id
        ),
        created_at=improvement.created_at,
        updated_at=improvement.updated_at,
    )


@router.get("", response_model=list[ImprovementRead])
def list_improvements(
    source_type: str | None = None,
    source_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ImprovementRead]:
    return [
        _to_read(db, improvement)
        for improvement in improvement_service.list_improvements(db, source_type, source_id)
    ]


@router.post("", response_model=ImprovementRead, status_code=201)
def create_improvement(
    data: ImprovementCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImprovementRead:
    return _to_read(db, improvement_service.create_improvement(db, data, actor_id))


# Declared before the /{improvement_id} routes, so "standing" isn't taken for an id.
@router.get("/standing", response_model=list[ImprovementAsOfRead])
def standing_as_of(as_of: date, db: Session = Depends(get_db)) -> list[ImprovementAsOfRead]:
    return [
        ImprovementAsOfRead(
            id=improvement.id,
            title=improvement.title,
            source=improvement.source,
            owner_id=improvement.owner_id,
            target_date=improvement.target_date,
            standing=_standing_read(standing),
        )
        for improvement, standing in improvement_service.standings_as_of(db, as_of)
    ]


@router.get("/{improvement_id}", response_model=ImprovementRead)
def get_improvement(improvement_id: int, db: Session = Depends(get_db)) -> ImprovementRead:
    return _to_read(db, improvement_service.get_improvement(db, improvement_id))


@router.put("/{improvement_id}", response_model=ImprovementRead)
def update_improvement(
    improvement_id: int,
    data: ImprovementUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImprovementRead:
    return _to_read(db, improvement_service.update_improvement(db, improvement_id, data, actor_id))


@router.delete("/{improvement_id}", status_code=204)
def delete_improvement(
    improvement_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    improvement_service.delete_improvement(db, improvement_id, actor_id)


@router.post("/{improvement_id}/status", response_model=ImprovementRead)
def change_status(
    improvement_id: int,
    data: ImprovementStatusUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImprovementRead:
    return _to_read(db, improvement_service.change_status(db, improvement_id, data, actor_id))


@router.post("/{improvement_id}/carry-out-as-change", response_model=ImprovementRead)
def carry_out_as_change(
    improvement_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ImprovementRead:
    return _to_read(db, improvement_service.carry_out_as_change(db, improvement_id, actor_id))
