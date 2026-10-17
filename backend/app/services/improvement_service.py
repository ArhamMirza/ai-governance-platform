"""Continual improvement of the AI management system -- ISO/IEC 42001 10.1.

Gated only by ordinary edit permission, like Changes and Objectives. Where
an improvement stands (proposed, accepted, overdue ...) is computed live
(app.core.improvement_tracking), never stored; only moving it on is a
person's call.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import improvement_tracking
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.core.improvement_tracking import ImprovementStanding
from app.models.ai_incident import AIIncident
from app.models.ai_objective import AIObjective
from app.models.audit_finding import AuditFinding
from app.models.concern import Concern
from app.models.corrective_action import CorrectiveAction
from app.models.improvement import Improvement, ImprovementSource, ImprovementStatus
from app.models.internal_audit import InternalAudit
from app.models.management_review_meeting import ManagementReviewMeeting
from app.repositories import improvement_repository
from app.schemas.change import ChangeCreate
from app.schemas.improvement import (
    ImprovementCreate,
    ImprovementStatusUpdate,
    ImprovementUpdate,
)
from app.services import audit_service, change_service, framework_service

ENTITY_TYPE = "Improvement"

# Each kind of record an improvement can arise from, and the source category
# that goes with it -- set from the record, so the two can't disagree.
_SOURCE_MODELS: dict[str, tuple[type, ImprovementSource]] = {
    "AuditFinding": (AuditFinding, ImprovementSource.INTERNAL_AUDIT),
    "ManagementReviewMeeting": (ManagementReviewMeeting, ImprovementSource.MANAGEMENT_REVIEW),
    "Concern": (Concern, ImprovementSource.CONCERN),
    "AIIncident": (AIIncident, ImprovementSource.INCIDENT),
    "CorrectiveAction": (CorrectiveAction, ImprovementSource.CORRECTIVE_ACTION),
    "AIObjective": (AIObjective, ImprovementSource.OBJECTIVE),
}


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


def standing(improvement: Improvement, as_of: date | None = None) -> ImprovementStanding:
    return improvement_tracking.standing(
        status=improvement.status,
        decided_on=improvement.decided_on,
        closed_on=improvement.closed_on,
        target_date=improvement.target_date,
        as_of=_today(as_of),
    )


def source_label(db: Session, improvement: Improvement) -> str | None:
    """What the source record is called, or None once it no longer exists.

    A concern is named by number only: concerns are readable by their
    handlers alone, and an improvement is readable by anyone in the
    organization, so nothing of what was reported is carried across."""
    if improvement.source_type is None or improvement.source_id is None:
        return None
    entry = _SOURCE_MODELS.get(improvement.source_type)
    if entry is None:
        return None
    record = db.get(entry[0], improvement.source_id)
    if record is None:
        return None
    if isinstance(record, AuditFinding):
        audit = db.get(InternalAudit, record.internal_audit_id)
        return f"Finding in {audit.title}" if audit else f"Audit finding #{record.id}"
    if isinstance(record, ManagementReviewMeeting):
        return f"Management review of {record.meeting_date}"
    if isinstance(record, Concern):
        return f"Concern #{record.id}"
    return record.title


def _get_or_raise(db: Session, improvement_id: int) -> Improvement:
    improvement = improvement_repository.get(db, improvement_id)
    if improvement is None:
        raise NotFoundError("Improvement", improvement_id)
    return improvement


def _validate(improvement: Improvement) -> None:
    """Checked against the improvement as it will be saved."""
    if improvement.target_date < improvement.raised_on:
        raise ValidationError("The target date can't be before the improvement was raised.")


def list_improvements(
    db: Session, source_type: str | None = None, source_id: int | None = None
) -> list[Improvement]:
    if source_type is not None and source_id is not None:
        return improvement_repository.list_for_source(db, source_type, source_id)
    return improvement_repository.list_all(db)


def get_improvement(db: Session, improvement_id: int) -> Improvement:
    return _get_or_raise(db, improvement_id)


def create_improvement(
    db: Session, data: ImprovementCreate, actor_id: int | None, today: date | None = None
) -> Improvement:
    fields = data.model_dump()
    if (data.source_type is None) != (data.source_id is None):
        raise ValidationError("A source record needs both its type and its id.")
    if data.source_type is not None and data.source_id is not None:
        model, category = _SOURCE_MODELS[data.source_type]
        if db.get(model, data.source_id) is None:
            raise NotFoundError(data.source_type, data.source_id)
        fields["source"] = category
    fields["raised_on"] = fields["raised_on"] or _today(today)
    improvement = Improvement(**fields, status=ImprovementStatus.PROPOSED)
    _validate(improvement)
    improvement = improvement_repository.create(db, improvement)
    audit_service.log(
        db,
        ENTITY_TYPE,
        improvement.id,
        "created",
        actor_id,
        {
            "title": improvement.title,
            "source": improvement.source,
            "source_type": improvement.source_type,
            "source_id": improvement.source_id,
        },
    )
    return improvement


def update_improvement(
    db: Session, improvement_id: int, data: ImprovementUpdate, actor_id: int | None
) -> Improvement:
    improvement = _get_or_raise(db, improvement_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("title", "raised_on", "target_date"):
        if required in changes and changes[required] is None:
            raise ValidationError("An improvement needs a title, a raised date and a target date.")
    for field, value in changes.items():
        setattr(improvement, field, value)
    try:
        _validate(improvement)
    except ValidationError:
        db.rollback()
        raise
    improvement = improvement_repository.save(db, improvement)
    audit_service.log(db, ENTITY_TYPE, improvement.id, "updated", actor_id, changes)
    return improvement


def change_status(
    db: Session,
    improvement_id: int,
    data: ImprovementStatusUpdate,
    actor_id: int | None,
    today: date | None = None,
) -> Improvement:
    """Moves an improvement on: accept it, implement it (with what came of
    it), decline it (with why), or put a closed one back to where it was.
    Dated, so a standing as of an earlier date still sees it as it was."""
    improvement = _get_or_raise(db, improvement_id)
    reference = _today(today)
    closed = improvement.status in improvement_tracking.CLOSED_STATES
    note = (data.note or "").strip() or None

    if data.action == "accept":
        if improvement.status != ImprovementStatus.PROPOSED:
            raise InvalidStatusTransitionError(
                f"Improvement {improvement_id} is {improvement.status}; "
                "only a proposed one can be accepted."
            )
        improvement.status = ImprovementStatus.ACCEPTED
        improvement.decided_on = reference
    elif data.action == "implement":
        if improvement.status != ImprovementStatus.ACCEPTED:
            raise InvalidStatusTransitionError(
                f"Improvement {improvement_id} is {improvement.status}; "
                "only an accepted one can be implemented."
            )
        if note is None:
            raise ValidationError("Record what changed and whether it worked.")
        improvement.status = ImprovementStatus.IMPLEMENTED
        improvement.closed_on = reference
        improvement.outcome = note
    elif data.action == "decline":
        if closed:
            raise InvalidStatusTransitionError(
                f"Improvement {improvement_id} is already {improvement.status}."
            )
        if note is None:
            raise ValidationError("Say why it isn't going ahead.")
        improvement.status = ImprovementStatus.DECLINED
        improvement.closed_on = reference
        improvement.decline_reason = note
    else:
        if not closed:
            raise InvalidStatusTransitionError(f"Improvement {improvement_id} is still open.")
        improvement.status = (
            ImprovementStatus.ACCEPTED
            if improvement.decided_on is not None
            else ImprovementStatus.PROPOSED
        )
        improvement.closed_on = None
        improvement.outcome = None
        improvement.decline_reason = None

    improvement = improvement_repository.save(db, improvement)
    audit_service.log(
        db,
        ENTITY_TYPE,
        improvement.id,
        f"status_{data.action}",
        actor_id,
        {"status": improvement.status, "note": note},
    )
    return improvement


def carry_out_as_change(
    db: Session, improvement_id: int, actor_id: int | None, today: date | None = None
) -> Improvement:
    """Plans an accepted improvement as a change to the management system
    (6.3), pre-filled from it, and links the two. Planned for its target
    date, or today if that has already passed."""
    improvement = _get_or_raise(db, improvement_id)
    if improvement.status != ImprovementStatus.ACCEPTED:
        raise InvalidStatusTransitionError(
            "Only an accepted improvement can be carried out as a change."
        )
    if improvement.change_id is not None:
        raise InvalidStatusTransitionError(
            f"Improvement {improvement_id} is already being carried out as a change."
        )
    reference = _today(today)
    change = change_service.create_change(
        db,
        ChangeCreate(
            title=improvement.title,
            description=improvement.description,
            reason=improvement.expected_benefit or improvement.description,
            owner_id=improvement.owner_id,
            raised_on=reference,
            planned_date=max(improvement.target_date, reference),
        ),
        actor_id,
    )
    improvement.change_id = change.id
    improvement = improvement_repository.save(db, improvement)
    audit_service.log(
        db, ENTITY_TYPE, improvement.id, "carried_out_as_change", actor_id, {"change_id": change.id}
    )
    return improvement


def unlink_change(db: Session, change_id: int, actor_id: int | None) -> None:
    """Called when a planned change is deleted: the improvement survives, no
    longer pointing at it."""
    for improvement in improvement_repository.list_for_change(db, change_id):
        improvement.change_id = None
        improvement_repository.save(db, improvement)
        audit_service.log(
            db, ENTITY_TYPE, improvement.id, "change_unlinked", actor_id, {"change_id": change_id}
        )


def delete_improvement(db: Session, improvement_id: int, actor_id: int | None) -> None:
    """Only while it's still a proposal -- once decided on, it's part of the
    record of how the management system was improved, so it's declined
    instead."""
    from app.services import evidence_service

    improvement = _get_or_raise(db, improvement_id)
    if improvement.status != ImprovementStatus.PROPOSED:
        raise InvalidStatusTransitionError(
            "This improvement has been decided on, so it can't be deleted; decline it instead."
        )
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, improvement_id)
    framework_service.delete_tags(db, ENTITY_TYPE, improvement_id)
    improvement_repository.delete(db, improvement)
    audit_service.log(
        db, ENTITY_TYPE, improvement_id, "deleted", actor_id, {"title": improvement.title}
    )


def standings_as_of(db: Session, as_of: date) -> list[tuple[Improvement, ImprovementStanding]]:
    """Every improvement that had been raised by `as_of`, with where it stood
    then -- what a management review meeting on that date was looking at."""
    return [
        (improvement, standing(improvement, as_of))
        for improvement in improvement_repository.list_all(db)
        if improvement_tracking.exists_as_of(improvement.raised_on, as_of)
    ]


def overdue_count(db: Session, today: date | None = None) -> int:
    """Open improvements past their target date -- for the dashboard."""
    return sum(
        1
        for improvement in improvement_repository.list_all(db)
        if standing(improvement, today).overdue
    )
