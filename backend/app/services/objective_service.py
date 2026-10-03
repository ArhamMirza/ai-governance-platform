"""AI objectives and their measurement -- ISO/IEC 42001 6.2 (objectives and
planning to achieve them) and 9.1 (monitoring and measurement).

Gated only by ordinary edit permission, like Suppliers and Competence. Where
an objective stands is computed live (app.core.objective_tracking), never
stored; only closing it is a person's decision.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import objective_tracking
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.core.objective_tracking import Reading, Standing
from app.models.ai_objective import AIObjective, ObjectiveKind, ObjectiveStatus
from app.models.ai_objective_ai_system import AIObjectiveAISystem
from app.models.objective_measurement import ObjectiveMeasurement
from app.repositories import objective_repository, policy_repository, sheet_repository
from app.schemas.objective import (
    MeasurementCreate,
    ObjectiveClose,
    ObjectiveCreate,
    ObjectiveUpdate,
)
from app.services import ai_system_inventory_service, audit_service, framework_service

ENTITY_TYPE = "AIObjective"
MEASUREMENT_ENTITY_TYPE = "ObjectiveMeasurement"

# Only meaningful for a measured objective; a milestone leaves them all empty.
_MEASURED_ONLY_FIELDS = (
    "metric_name",
    "unit",
    "direction",
    "target_value",
    "baseline_value",
    "measurement_interval_months",
    "first_measurement_due",
)


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


def standing(
    objective: AIObjective, measurements: list[ObjectiveMeasurement], as_of: date | None = None
) -> Standing:
    return objective_tracking.standing(
        kind=objective.kind,
        status=objective.status,
        closed_on=objective.closed_on,
        direction=objective.direction,
        target_value=objective.target_value,
        target_date=objective.target_date,
        interval_months=objective.measurement_interval_months,
        first_measurement_due=objective.first_measurement_due,
        readings=[Reading(m.measured_on, m.value) for m in measurements],
        as_of=_today(as_of),
    )


def measurements_by_objective(db: Session) -> dict[int, list[ObjectiveMeasurement]]:
    """Every objective's readings in one query, in the order recorded -- for
    list views and the dashboard rather than one query per objective."""
    readings: dict[int, list[ObjectiveMeasurement]] = defaultdict(list)
    for measurement in objective_repository.list_measurements(db):
        readings[measurement.objective_id].append(measurement)
    return readings


def links_by_objective(db: Session) -> dict[int, list[AIObjectiveAISystem]]:
    linked: dict[int, list[AIObjectiveAISystem]] = defaultdict(list)
    for link in objective_repository.list_links(db):
        linked[link.objective_id].append(link)
    return linked


def _get_or_raise(db: Session, objective_id: int) -> AIObjective:
    objective = objective_repository.get(db, objective_id)
    if objective is None:
        raise NotFoundError("AIObjective", objective_id)
    return objective


def _validate(db: Session, objective: AIObjective) -> None:
    """Checked against the objective as it will be saved, so no partial
    update can leave it half-configured."""
    if objective.kind == ObjectiveKind.MEASURED:
        if not objective.metric_name or objective.direction is None:
            raise ValidationError("A measured objective needs a metric and a target direction.")
        if objective.target_value is None:
            raise ValidationError("A measured objective needs a target value.")
        if (objective.measurement_interval_months is None) != (
            objective.first_measurement_due is None
        ):
            raise ValidationError(
                "Set both how often the objective is measured and when the first "
                "measurement is due, or neither."
            )
    else:
        if any(getattr(objective, field) is not None for field in _MEASURED_ONLY_FIELDS):
            raise ValidationError(
                "A milestone objective has no metric, target value or measurement schedule."
            )
        if objective.target_date is None:
            raise ValidationError("A milestone objective needs a target date.")
    if objective.target_date is not None and objective.target_date < objective.established_on:
        raise ValidationError("The target date can't be before the objective was set.")
    if objective.policy_id is not None and policy_repository.get(db, objective.policy_id) is None:
        raise NotFoundError("Policy", objective.policy_id)


def _validate_ai_system_rows(db: Session, row_ids: list[int]) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    for row_id in row_ids:
        row = sheet_repository.get_row(db, row_id)
        if row is None or row.sheet_id != inventory_sheet.id:
            raise NotFoundError("AISystemRow", row_id)


def list_objectives(db: Session, ai_system_row_id: int | None = None) -> list[AIObjective]:
    objectives = objective_repository.list_all(db)
    if ai_system_row_id is None:
        return objectives
    linked = {
        link.objective_id
        for link in objective_repository.list_links_for_ai_system(db, ai_system_row_id)
    }
    return [objective for objective in objectives if objective.id in linked]


def get_objective(db: Session, objective_id: int) -> AIObjective:
    return _get_or_raise(db, objective_id)


def list_measurements(db: Session, objective_id: int) -> list[ObjectiveMeasurement]:
    return objective_repository.list_measurements_for_objective(db, objective_id)


def linked_ai_system_ids(db: Session, objective_id: int) -> list[int]:
    return [
        link.ai_system_row_id
        for link in objective_repository.list_links_for_objective(db, objective_id)
    ]


def create_objective(
    db: Session, data: ObjectiveCreate, actor_id: int | None, today: date | None = None
) -> AIObjective:
    fields = data.model_dump()
    fields["established_on"] = fields["established_on"] or _today(today)
    objective = AIObjective(**fields, status=ObjectiveStatus.ACTIVE)
    _validate(db, objective)
    objective = objective_repository.create(db, objective)
    audit_service.log(
        db, ENTITY_TYPE, objective.id, "created", actor_id, {"title": objective.title}
    )
    return objective


def update_objective(
    db: Session, objective_id: int, data: ObjectiveUpdate, actor_id: int | None
) -> AIObjective:
    objective = _get_or_raise(db, objective_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("established_on", objective.established_on) is None:
        raise ValidationError("An objective needs the date it was set.")
    if (
        changes.get("kind") == ObjectiveKind.MILESTONE
        and objective.kind == ObjectiveKind.MEASURED
        and objective_repository.list_measurements_for_objective(db, objective_id)
    ):
        raise ValidationError(
            "This objective already has readings, so it can't become a milestone."
        )
    for field, value in changes.items():
        setattr(objective, field, value)
    try:
        _validate(db, objective)
    except (ValidationError, NotFoundError):
        db.rollback()
        raise
    objective = objective_repository.save(db, objective)
    audit_service.log(db, ENTITY_TYPE, objective.id, "updated", actor_id, changes)
    return objective


def close_objective(
    db: Session,
    objective_id: int,
    data: ObjectiveClose,
    actor_id: int | None,
    today: date | None = None,
) -> AIObjective:
    """Records the person's call on how it ended -- achieved, not achieved,
    withdrawn. Dated, so a standing as of an earlier date still sees it open."""
    objective = _get_or_raise(db, objective_id)
    if data.status == ObjectiveStatus.ACTIVE:
        raise ValidationError("Close an objective as achieved, not achieved or withdrawn.")
    if objective.status != ObjectiveStatus.ACTIVE:
        raise InvalidStatusTransitionError(f"Objective {objective_id} is already closed.")
    objective.status = data.status
    objective.closed_on = _today(today)
    objective.closure_note = data.closure_note
    objective = objective_repository.save(db, objective)
    audit_service.log(
        db,
        ENTITY_TYPE,
        objective.id,
        "closed",
        actor_id,
        {"status": objective.status, "closed_on": objective.closed_on},
    )
    return objective


def reopen_objective(db: Session, objective_id: int, actor_id: int | None) -> AIObjective:
    objective = _get_or_raise(db, objective_id)
    if objective.status == ObjectiveStatus.ACTIVE:
        raise InvalidStatusTransitionError(f"Objective {objective_id} is already open.")
    previous = objective.status
    objective.status = ObjectiveStatus.ACTIVE
    objective.closed_on = None
    objective.closure_note = None
    objective = objective_repository.save(db, objective)
    audit_service.log(db, ENTITY_TYPE, objective.id, "reopened", actor_id, {"was": previous})
    return objective


def set_ai_systems(
    db: Session, objective_id: int, ai_system_row_ids: list[int], actor_id: int | None
) -> AIObjective:
    objective = _get_or_raise(db, objective_id)
    _validate_ai_system_rows(db, ai_system_row_ids)
    objective_repository.replace_links(db, objective_id, ai_system_row_ids)
    audit_service.log(
        db,
        ENTITY_TYPE,
        objective_id,
        "ai_systems_updated",
        actor_id,
        {"ai_system_row_ids": sorted(set(ai_system_row_ids))},
    )
    return objective


def record_measurement(
    db: Session,
    objective_id: int,
    data: MeasurementCreate,
    actor_id: int | None,
    today: date | None = None,
) -> ObjectiveMeasurement:
    objective = _get_or_raise(db, objective_id)
    if objective.kind != ObjectiveKind.MEASURED:
        raise ValidationError("A milestone objective has no metric to record readings for.")
    if objective.status != ObjectiveStatus.ACTIVE:
        raise InvalidStatusTransitionError(
            "This objective is closed; reopen it to record a reading."
        )
    if data.measured_on > _today(today):
        raise ValidationError("A reading can't be dated in the future.")
    measurement = objective_repository.create_measurement(
        db,
        ObjectiveMeasurement(
            objective_id=objective_id,
            measured_on=data.measured_on,
            value=data.value,
            note=data.note,
            recorded_by=actor_id,
        ),
    )
    audit_service.log(
        db,
        ENTITY_TYPE,
        objective_id,
        "measurement_recorded",
        actor_id,
        {
            "measurement_id": measurement.id,
            "measured_on": measurement.measured_on,
            "value": measurement.value,
        },
    )
    return measurement


def delete_measurement(db: Session, measurement_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope, matching supplier_service:
    # evidence_service imports services back.
    from app.services import evidence_service

    measurement = objective_repository.get_measurement(db, measurement_id)
    if measurement is None:
        raise NotFoundError("ObjectiveMeasurement", measurement_id)
    objective_id = measurement.objective_id
    evidence_service.delete_all_for_entity(db, MEASUREMENT_ENTITY_TYPE, measurement_id)
    objective_repository.delete_measurement(db, measurement)
    audit_service.log(
        db,
        ENTITY_TYPE,
        objective_id,
        "measurement_deleted",
        actor_id,
        {"measurement_id": measurement_id},
    )


def delete_objective(db: Session, objective_id: int, actor_id: int | None) -> None:
    """Only while nothing has been measured against it -- after that the
    readings are monitoring evidence (9.1), so it's closed as withdrawn
    instead."""
    from app.services import evidence_service

    objective = _get_or_raise(db, objective_id)
    if objective_repository.list_measurements_for_objective(db, objective_id):
        raise InvalidStatusTransitionError(
            "This objective has recorded readings, so it can't be deleted; "
            "close it as withdrawn instead."
        )
    objective_repository.delete_links(
        db, objective_repository.list_links_for_objective(db, objective_id)
    )
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, objective_id)
    framework_service.delete_tags(db, ENTITY_TYPE, objective_id)
    objective_repository.delete(db, objective)
    audit_service.log(
        db, ENTITY_TYPE, objective_id, "deleted", actor_id, {"title": objective.title}
    )


def unlink_ai_system(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    """Drops every objective's link to an AI system being deleted. The
    objectives themselves survive -- they belong to the management system,
    not to any one AI system."""
    links = objective_repository.list_links_for_ai_system(db, ai_system_row_id)
    if not links:
        return
    objective_repository.delete_links(db, links)
    for link in links:
        audit_service.log(
            db,
            ENTITY_TYPE,
            link.objective_id,
            "ai_system_unlinked",
            actor_id,
            {"ai_system_row_id": ai_system_row_id},
        )


def unlink_policy(db: Session, policy_id: int, actor_id: int | None) -> None:
    """Clears the policy reference on objectives pointing at a (draft)
    policy being deleted."""
    for objective in objective_repository.list_for_policy(db, policy_id):
        objective.policy_id = None
        objective_repository.save(db, objective)
        audit_service.log(
            db, ENTITY_TYPE, objective.id, "policy_unlinked", actor_id, {"policy_id": policy_id}
        )


def standings_as_of(db: Session, as_of: date) -> list[tuple[AIObjective, Standing]]:
    """Every objective that had been set by `as_of`, with where it stood
    then -- what a management review meeting on that date was looking at."""
    readings = measurements_by_objective(db)
    return [
        (objective, standing(objective, readings[objective.id], as_of))
        for objective in objective_repository.list_all(db)
        if objective.established_on <= as_of
    ]


@dataclass(frozen=True)
class AttentionCounts:
    # Active objectives off track, or past their target date unmet.
    falling_short: int
    measurement_overdue: int


def attention_counts(db: Session, today: date | None = None) -> AttentionCounts:
    """For the dashboard -- every objective's standing worked out once."""
    readings = measurements_by_objective(db)
    standings = [
        standing(objective, readings[objective.id], today)
        for objective in objective_repository.list_all(db)
    ]
    return AttentionCounts(
        falling_short=sum(1 for s in standings if s.state in objective_tracking.FALLING_SHORT),
        measurement_overdue=sum(1 for s in standings if s.measurement_overdue),
    )
