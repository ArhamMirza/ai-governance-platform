from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.competence_requirement import CompetenceRequirement
from app.repositories import competence_repository
from app.schemas.competence import (
    CompetenceRecordCreate,
    CompetenceRequirementCreate,
    CompetenceRequirementUpdate,
)
from app.services import competence_service, framework_service, governance_role_service

TODAY = date(2026, 6, 15)


# ---------- person_status ----------


def test_never_completed_is_missing() -> None:
    assert competence_service.person_status(12, [], TODAY) == ("missing", None, None)


def test_a_one_off_requirement_stays_current_forever() -> None:
    assert competence_service.person_status(None, [date(2010, 1, 1)], TODAY) == (
        "current",
        date(2010, 1, 1),
        None,
    )


def test_a_recurring_requirement_is_current_until_its_refresh_is_due() -> None:
    assert competence_service.person_status(12, [date(2026, 1, 10)], TODAY) == (
        "current",
        date(2026, 1, 10),
        date(2027, 1, 10),
    )


def test_not_expired_on_the_due_date_itself() -> None:
    status, _, _ = competence_service.person_status(6, [date(2025, 12, 15)], TODAY)

    assert status == "current"


def test_expired_the_day_after_the_refresh_was_due() -> None:
    status, _, next_due = competence_service.person_status(6, [date(2025, 12, 14)], TODAY)

    assert status == "expired"
    assert next_due == date(2026, 6, 14)


def test_only_the_latest_completion_counts() -> None:
    status, last, _ = competence_service.person_status(
        6, [date(2024, 1, 1), date(2026, 5, 1)], TODAY
    )

    assert status == "current"
    assert last == date(2026, 5, 1)


# ---------- who is required ----------


def test_a_role_requirement_needs_only_active_holders() -> None:
    requirement = CompetenceRequirement(governance_role_id=7)

    assert competence_service.required_user_ids(
        requirement, active_user_ids={1, 2, 3}, holders_by_role={7: {2, 3, 4}}
    ) == {2, 3}


def test_an_everyone_requirement_needs_every_active_user() -> None:
    requirement = CompetenceRequirement(governance_role_id=None)

    assert competence_service.required_user_ids(
        requirement, active_user_ids={1, 2}, holders_by_role={7: {9}}
    ) == {1, 2}


def test_a_vacant_role_requires_nobody() -> None:
    requirement = CompetenceRequirement(governance_role_id=7)

    assert competence_service.required_user_ids(requirement, {1, 2}, {}) == set()


# ---------- service ----------


def make_role(db: Session, name: str = "Bias Reviewer") -> int:
    return governance_role_service.create_role(
        db, name, "Reviews models for bias", None, None, None
    ).id


def make_requirement(db: Session, **overrides) -> CompetenceRequirement:
    data = {"title": "Bias testing fundamentals"}
    data.update(overrides)
    return competence_service.create_requirement(
        db, CompetenceRequirementCreate(**data), actor_id=None
    )


def test_role_holders_show_up_as_missing_until_they_complete_it(
    db_session: Session, make_user
) -> None:
    role_id = make_role(db_session)
    holder, bystander = make_user(), make_user()
    governance_role_service.assign_user(db_session, role_id, holder.id, actor_id=None)
    requirement = make_requirement(db_session, governance_role_id=role_id)

    people = competence_service.people_for(db_session, requirement, TODAY)
    assert [(p.user_id, p.status) for p in people] == [(holder.id, "missing")]
    assert bystander.id not in {p.user_id for p in people}

    competence_service.record_completion(
        db_session,
        requirement.id,
        CompetenceRecordCreate(user_id=holder.id, completed_on=date(2026, 6, 1)),
        actor_id=None,
        today=TODAY,
    )

    people = competence_service.people_for(db_session, requirement, TODAY)
    assert [(p.user_id, p.status) for p in people] == [(holder.id, "current")]


def test_deactivated_users_drop_out_of_everyone_requirements(
    db_session: Session, make_user
) -> None:
    active, deactivated = make_user(), make_user(is_active=False)
    requirement = make_requirement(db_session)

    required = {p.user_id for p in competence_service.people_for(db_session, requirement, TODAY)}

    assert active.id in required
    assert deactivated.id not in required


def test_a_requirement_for_an_unknown_role_is_refused(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        make_requirement(db_session, governance_role_id=9999)


def test_retargeting_to_everyone(db_session: Session) -> None:
    requirement = make_requirement(db_session, governance_role_id=make_role(db_session))

    updated = competence_service.update_requirement(
        db_session,
        requirement.id,
        CompetenceRequirementUpdate(governance_role_id=None),
        actor_id=None,
    )

    assert updated.governance_role_id is None


def test_a_completion_cannot_be_dated_in_the_future(db_session: Session, make_user) -> None:
    requirement = make_requirement(db_session)

    with pytest.raises(ValidationError):
        competence_service.record_completion(
            db_session,
            requirement.id,
            CompetenceRecordCreate(user_id=make_user().id, completed_on=date(2026, 6, 16)),
            actor_id=None,
            today=TODAY,
        )


def test_deleting_a_role_a_requirement_targets_is_refused(db_session: Session) -> None:
    role_id = make_role(db_session)
    make_requirement(db_session, governance_role_id=role_id)

    with pytest.raises(ConflictError):
        governance_role_service.delete_role(db_session, role_id, actor_id=None)


def test_deleting_a_requirement_removes_its_records_and_tags(
    db_session: Session, make_user
) -> None:
    requirement = make_requirement(db_session)
    record = competence_service.record_completion(
        db_session,
        requirement.id,
        CompetenceRecordCreate(user_id=make_user().id, completed_on=date(2026, 6, 1)),
        actor_id=None,
        today=TODAY,
    )
    framework_service.set_tags(
        db_session,
        competence_service.REQUIREMENT_ENTITY_TYPE,
        requirement.id,
        [1],
        actor_id=None,
    )

    competence_service.delete_requirement(db_session, requirement.id, actor_id=None)

    assert competence_repository.get_record(db_session, record.id) is None
    assert (
        framework_service.get_tags(
            db_session, competence_service.REQUIREMENT_ENTITY_TYPE, requirement.id
        )
        == []
    )


def test_deleting_a_record_puts_the_person_back_to_missing(db_session: Session, make_user) -> None:
    person = make_user()
    requirement = make_requirement(db_session)
    record = competence_service.record_completion(
        db_session,
        requirement.id,
        CompetenceRecordCreate(user_id=person.id, completed_on=date(2026, 6, 1)),
        actor_id=None,
        today=TODAY,
    )

    competence_service.delete_record(db_session, record.id, actor_id=None)

    statuses = {
        p.user_id: p.status for p in competence_service.people_for(db_session, requirement, TODAY)
    }
    assert statuses[person.id] == "missing"
