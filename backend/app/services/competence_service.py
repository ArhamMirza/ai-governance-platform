"""Competence and awareness -- ISO/IEC 42001 Clauses 7.2/7.3.

A requirement says what's needed and by whom (one governance role, or
everyone); a record says one person completed it on a date. Everything in
between -- who is required, and whether each of them is current, expired or
missing -- is computed live from roles, users and records, never stored, so
it can't drift from any of them: assign someone a role and they're on the
hook; deactivate them and they drop off.

Gated only by ordinary edit permission, like Internal Audit and Management
Review: these are operational records, not documents needing sign-off.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import audit_schedule
from app.core.exceptions import NotFoundError, ValidationError
from app.models.competence_record import CompetenceRecord
from app.models.competence_requirement import CompetenceRequirement
from app.repositories import competence_repository, governance_role_repository, user_repository
from app.schemas.competence import (
    CompetenceRecordCreate,
    CompetenceRequirementCreate,
    CompetenceRequirementUpdate,
    CompetenceStatus,
    PersonCompetence,
)
from app.services import audit_service, framework_service

REQUIREMENT_ENTITY_TYPE = "CompetenceRequirement"
RECORD_ENTITY_TYPE = "CompetenceRecord"


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


def person_status(
    refresh_interval_months: int | None, completed_dates: list[date], today: date
) -> tuple[CompetenceStatus, date | None, date | None]:
    """(status, last completed, next due) for one person. Only the latest
    completion counts -- refreshing a recurring requirement adds a record
    rather than editing the old one."""
    if not completed_dates:
        return "missing", None, None
    latest = max(completed_dates)
    if refresh_interval_months is None:
        return "current", latest, None
    next_due = audit_schedule.next_audit_date(latest, refresh_interval_months)
    status: CompetenceStatus = (
        "expired" if audit_schedule.is_audit_overdue(next_due, today) else "current"
    )
    return status, latest, next_due


def required_user_ids(
    requirement: CompetenceRequirement,
    active_user_ids: set[int],
    holders_by_role: dict[int, set[int]],
) -> set[int]:
    """Active holders of the requirement's role, or every active user when
    it targets no role. A vacant role requires nobody."""
    if requirement.governance_role_id is None:
        return set(active_user_ids)
    return holders_by_role.get(requirement.governance_role_id, set()) & active_user_ids


@dataclass(frozen=True)
class _Snapshot:
    """Everything the standings depend on, loaded once -- a handful of bulk
    queries rather than one per requirement or person."""

    active_user_ids: set[int]
    holders_by_role: dict[int, set[int]]
    records_by_requirement: dict[int, list[CompetenceRecord]]


def _snapshot(db: Session) -> _Snapshot:
    holders_by_role: dict[int, set[int]] = defaultdict(set)
    for assignment in governance_role_repository.list_all_assignments(db):
        holders_by_role[assignment.governance_role_id].add(assignment.user_id)
    records_by_requirement: dict[int, list[CompetenceRecord]] = defaultdict(list)
    for record in competence_repository.list_records(db):
        records_by_requirement[record.requirement_id].append(record)
    return _Snapshot(
        active_user_ids={user.id for user in user_repository.list_all(db) if user.is_active},
        holders_by_role=holders_by_role,
        records_by_requirement=records_by_requirement,
    )


def _people(
    requirement: CompetenceRequirement, snapshot: _Snapshot, today: date
) -> list[PersonCompetence]:
    dates_by_user: dict[int, list[date]] = defaultdict(list)
    for record in snapshot.records_by_requirement.get(requirement.id, []):
        dates_by_user[record.user_id].append(record.completed_on)
    people = []
    for user_id in sorted(
        required_user_ids(requirement, snapshot.active_user_ids, snapshot.holders_by_role)
    ):
        status, last, next_due = person_status(
            requirement.refresh_interval_months, dates_by_user[user_id], today
        )
        people.append(
            PersonCompetence(
                user_id=user_id, status=status, last_completed_on=last, next_due=next_due
            )
        )
    return people


def standings(
    db: Session, today: date | None = None
) -> list[tuple[CompetenceRequirement, list[PersonCompetence]]]:
    """Every requirement with each required person's standing."""
    snapshot = _snapshot(db)
    reference = _today(today)
    return [
        (requirement, _people(requirement, snapshot, reference))
        for requirement in competence_repository.list_requirements(db)
    ]


def people_for(
    db: Session, requirement: CompetenceRequirement, today: date | None = None
) -> list[PersonCompetence]:
    return _people(requirement, _snapshot(db), _today(today))


def gap_count(people: list[PersonCompetence]) -> int:
    return sum(1 for person in people if person.status != "current")


def _get_or_raise(db: Session, requirement_id: int) -> CompetenceRequirement:
    requirement = competence_repository.get_requirement(db, requirement_id)
    if requirement is None:
        raise NotFoundError("CompetenceRequirement", requirement_id)
    return requirement


def _validate_role(db: Session, role_id: int | None) -> None:
    if role_id is not None and governance_role_repository.get(db, role_id) is None:
        raise NotFoundError("GovernanceRole", role_id)


def get_requirement(db: Session, requirement_id: int) -> CompetenceRequirement:
    return _get_or_raise(db, requirement_id)


def list_records(db: Session, requirement_id: int) -> list[CompetenceRecord]:
    _get_or_raise(db, requirement_id)
    return competence_repository.list_records_for_requirement(db, requirement_id)


def create_requirement(
    db: Session, data: CompetenceRequirementCreate, actor_id: int | None
) -> CompetenceRequirement:
    _validate_role(db, data.governance_role_id)
    requirement = competence_repository.create_requirement(
        db,
        CompetenceRequirement(
            title=data.title,
            description=data.description,
            governance_role_id=data.governance_role_id,
            refresh_interval_months=data.refresh_interval_months,
        ),
    )
    audit_service.log(
        db,
        REQUIREMENT_ENTITY_TYPE,
        requirement.id,
        "created",
        actor_id,
        {"title": requirement.title},
    )
    return requirement


def update_requirement(
    db: Session, requirement_id: int, data: CompetenceRequirementUpdate, actor_id: int | None
) -> CompetenceRequirement:
    requirement = _get_or_raise(db, requirement_id)
    changes = data.model_dump(exclude_unset=True)
    if "governance_role_id" in changes:
        _validate_role(db, changes["governance_role_id"])
    for field, value in changes.items():
        setattr(requirement, field, value)
    requirement = competence_repository.save_requirement(db, requirement)
    audit_service.log(db, REQUIREMENT_ENTITY_TYPE, requirement.id, "updated", actor_id, changes)
    return requirement


def delete_requirement(db: Session, requirement_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope, matching
    # corrective_action_service: evidence_service imports services back.
    from app.services import evidence_service

    requirement = _get_or_raise(db, requirement_id)
    for record in competence_repository.list_records_for_requirement(db, requirement_id):
        evidence_service.delete_all_for_entity(db, RECORD_ENTITY_TYPE, record.id)
        competence_repository.delete_record(db, record)
    competence_repository.delete_requirement(db, requirement)
    framework_service.delete_tags(db, REQUIREMENT_ENTITY_TYPE, requirement_id)
    audit_service.log(
        db,
        REQUIREMENT_ENTITY_TYPE,
        requirement_id,
        "deleted",
        actor_id,
        {"title": requirement.title},
    )


def record_completion(
    db: Session,
    requirement_id: int,
    data: CompetenceRecordCreate,
    actor_id: int | None,
    today: date | None = None,
) -> CompetenceRecord:
    _get_or_raise(db, requirement_id)
    if user_repository.get(db, data.user_id) is None:
        raise NotFoundError("User", data.user_id)
    if data.completed_on > _today(today):
        raise ValidationError("A completion can't be dated in the future.")
    record = competence_repository.create_record(
        db,
        CompetenceRecord(
            requirement_id=requirement_id,
            user_id=data.user_id,
            completed_on=data.completed_on,
            notes=data.notes,
            recorded_by=actor_id,
        ),
    )
    audit_service.log(
        db,
        REQUIREMENT_ENTITY_TYPE,
        requirement_id,
        "completion_recorded",
        actor_id,
        {"record_id": record.id, "user_id": data.user_id, "completed_on": data.completed_on},
    )
    return record


def delete_record(db: Session, record_id: int, actor_id: int | None) -> None:
    from app.services import evidence_service

    record = competence_repository.get_record(db, record_id)
    if record is None:
        raise NotFoundError("CompetenceRecord", record_id)
    requirement_id, user_id = record.requirement_id, record.user_id
    evidence_service.delete_all_for_entity(db, RECORD_ENTITY_TYPE, record_id)
    competence_repository.delete_record(db, record)
    audit_service.log(
        db,
        REQUIREMENT_ENTITY_TYPE,
        requirement_id,
        "completion_deleted",
        actor_id,
        {"record_id": record_id, "user_id": user_id},
    )
