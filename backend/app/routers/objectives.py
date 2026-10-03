from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.objective_tracking import Standing
from app.dependencies import get_current_actor_id
from app.models.ai_objective import AIObjective
from app.models.objective_measurement import ObjectiveMeasurement
from app.schemas.objective import (
    MeasurementCreate,
    MeasurementRead,
    ObjectiveAISystemsUpdate,
    ObjectiveAsOfRead,
    ObjectiveClose,
    ObjectiveCreate,
    ObjectiveDetailRead,
    ObjectiveRead,
    ObjectiveStandingRead,
    ObjectiveUpdate,
)
from app.services import framework_service, objective_service

router = APIRouter(prefix="/objectives", tags=["objectives"])


def _standing_read(standing: Standing) -> ObjectiveStandingRead:
    return ObjectiveStandingRead(
        state=standing.state,
        latest_value=standing.latest_value,
        latest_on=standing.latest_on,
        next_measurement_due=standing.next_measurement_due,
        measurement_overdue=standing.measurement_overdue,
    )


def _to_read(
    db: Session,
    objective: AIObjective,
    measurements: list[ObjectiveMeasurement],
    ai_system_row_ids: list[int],
) -> ObjectiveRead:
    return ObjectiveRead(
        id=objective.id,
        title=objective.title,
        description=objective.description,
        kind=objective.kind,
        owner_id=objective.owner_id,
        policy_id=objective.policy_id,
        established_on=objective.established_on,
        target_date=objective.target_date,
        planned_actions=objective.planned_actions,
        resources=objective.resources,
        evaluation_method=objective.evaluation_method,
        metric_name=objective.metric_name,
        unit=objective.unit,
        direction=objective.direction,
        target_value=objective.target_value,
        baseline_value=objective.baseline_value,
        measurement_interval_months=objective.measurement_interval_months,
        first_measurement_due=objective.first_measurement_due,
        status=objective.status,
        closed_on=objective.closed_on,
        closure_note=objective.closure_note,
        ai_system_row_ids=ai_system_row_ids,
        standing=_standing_read(objective_service.standing(objective, measurements)),
        framework_tags=framework_service.get_tags(db, objective_service.ENTITY_TYPE, objective.id),
        created_at=objective.created_at,
        updated_at=objective.updated_at,
    )


def _to_detail(db: Session, objective: AIObjective) -> ObjectiveDetailRead:
    measurements = objective_service.list_measurements(db, objective.id)
    base = _to_read(
        db, objective, measurements, objective_service.linked_ai_system_ids(db, objective.id)
    )
    return ObjectiveDetailRead(
        **base.model_dump(),
        # Newest first for display; standing above was computed from them
        # in the order recorded.
        measurements=[
            MeasurementRead.model_validate(m)
            for m in sorted(measurements, key=lambda m: (m.measured_on, m.id), reverse=True)
        ],
    )


@router.get("", response_model=list[ObjectiveRead])
def list_objectives(
    ai_system_row_id: int | None = None, db: Session = Depends(get_db)
) -> list[ObjectiveRead]:
    readings = objective_service.measurements_by_objective(db)
    links = objective_service.links_by_objective(db)
    return [
        _to_read(
            db,
            objective,
            readings[objective.id],
            [link.ai_system_row_id for link in links[objective.id]],
        )
        for objective in objective_service.list_objectives(db, ai_system_row_id)
    ]


@router.post("", response_model=ObjectiveDetailRead, status_code=201)
def create_objective(
    data: ObjectiveCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ObjectiveDetailRead:
    return _to_detail(db, objective_service.create_objective(db, data, actor_id))


# Declared before the /{objective_id} routes, so "standing" and
# "measurements" aren't taken for an objective id.
@router.get("/standing", response_model=list[ObjectiveAsOfRead])
def standing_as_of(as_of: date, db: Session = Depends(get_db)) -> list[ObjectiveAsOfRead]:
    return [
        ObjectiveAsOfRead(
            id=objective.id,
            title=objective.title,
            kind=objective.kind,
            metric_name=objective.metric_name,
            unit=objective.unit,
            direction=objective.direction,
            target_value=objective.target_value,
            target_date=objective.target_date,
            owner_id=objective.owner_id,
            standing=_standing_read(standing),
        )
        for objective, standing in objective_service.standings_as_of(db, as_of)
    ]


@router.delete("/measurements/{measurement_id}", status_code=204)
def delete_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    objective_service.delete_measurement(db, measurement_id, actor_id)


@router.get("/{objective_id}", response_model=ObjectiveDetailRead)
def get_objective(objective_id: int, db: Session = Depends(get_db)) -> ObjectiveDetailRead:
    return _to_detail(db, objective_service.get_objective(db, objective_id))


@router.put("/{objective_id}", response_model=ObjectiveDetailRead)
def update_objective(
    objective_id: int,
    data: ObjectiveUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ObjectiveDetailRead:
    return _to_detail(db, objective_service.update_objective(db, objective_id, data, actor_id))


@router.delete("/{objective_id}", status_code=204)
def delete_objective(
    objective_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    objective_service.delete_objective(db, objective_id, actor_id)


@router.post("/{objective_id}/close", response_model=ObjectiveDetailRead)
def close_objective(
    objective_id: int,
    data: ObjectiveClose,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ObjectiveDetailRead:
    return _to_detail(db, objective_service.close_objective(db, objective_id, data, actor_id))


@router.post("/{objective_id}/reopen", response_model=ObjectiveDetailRead)
def reopen_objective(
    objective_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ObjectiveDetailRead:
    return _to_detail(db, objective_service.reopen_objective(db, objective_id, actor_id))


@router.put("/{objective_id}/ai-systems", response_model=ObjectiveDetailRead)
def set_ai_systems(
    objective_id: int,
    data: ObjectiveAISystemsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ObjectiveDetailRead:
    objective = objective_service.set_ai_systems(db, objective_id, data.ai_system_row_ids, actor_id)
    return _to_detail(db, objective)


@router.post("/{objective_id}/measurements", response_model=MeasurementRead, status_code=201)
def record_measurement(
    objective_id: int,
    data: MeasurementCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> MeasurementRead:
    measurement = objective_service.record_measurement(db, objective_id, data, actor_id)
    return MeasurementRead.model_validate(measurement)
