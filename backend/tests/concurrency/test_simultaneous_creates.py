"""Two requests that each check, find nothing, and create.

Every one of these used to produce a duplicate or a 500. What they should
produce instead splits in two: for a record that exists to carry state for
something else, both callers wanted the same row, so the loser takes the
winner's; for a record a second of which is a mistake, the loser is told so
in the same words a sequential caller would have heard.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.governance_role_seed_data import DEFAULT_ROLES
from app.core.security import hash_password
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment
from app.models.governance_role_delegation import GovernanceRoleDelegation
from app.models.impact_assessment import ImpactAssessment
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import Sheet
from app.models.user import User, UserRole
from app.repositories import (
    ai_system_lifecycle_repository,
    governance_role_repository,
    impact_assessment_repository,
    risk_assessment_repository,
    sheet_repository,
)
from app.schemas.impact_assessment import ImpactAssessmentCreate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    data_inventory_service,
    governance_role_service,
    impact_assessment_service,
    risk_assessment_service,
)
from tests.concurrency.conftest import barrier, errors, pause_after, run_together
from tests.helpers import complete_impact_assessment_db


def count(session: Session, model, *where) -> int:
    return session.scalar(select(func.count()).select_from(model).where(*where))


def make_admin(session: Session, email: str) -> User:
    user = User(
        name=email.split("@")[0],
        email=email,
        password_hash=hash_password("password123"),
        role=UserRole.ADMIN,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def caigo_role(session: Session) -> GovernanceRole:
    return session.scalars(
        select(GovernanceRole).where(GovernanceRole.name == DEFAULT_ROLES[0][0])
    ).one()


# ---------- records both callers wanted to exist ----------


def test_two_first_requests_provision_one_data_inventory_sheet(
    concurrent_sessions, monkeypatch
) -> None:
    pause_after(monkeypatch, sheet_repository, "get_by_entity_type", barrier())

    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: data_inventory_service.get_or_create_sheet(session).id,
    )

    assert list(errors(outcomes)) == []
    assert outcomes[0].value == outcomes[1].value
    with concurrent_sessions() as session:
        assert count(session, Sheet, Sheet.entity_type == "DataInventory") == 1


def test_two_first_requests_create_one_lifecycle(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id
    # add_row creates the life cycle eagerly; dropping it puts the row back in
    # the state get_or_create exists for -- one recreated by an xlsx import.
    ai_system_lifecycle_repository.delete_for_ai_system(setup_session, row_id)

    pause_after(monkeypatch, ai_system_lifecycle_repository, "get_for_ai_system", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: ai_system_lifecycle_service.get_or_create(session, row_id).id,
    )

    assert list(errors(outcomes)) == []
    assert outcomes[0].value == outcomes[1].value
    with concurrent_sessions() as session:
        assert count(session, AISystemLifecycle) == 1


# ---------- records a second of which is a mistake ----------


def test_two_simultaneous_risk_assessments_leave_one(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    make_admin(setup_session, "owner@example.com")
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id
    complete_impact_assessment_db(setup_session, row_id)
    setup_session.commit()

    pause_after(monkeypatch, risk_assessment_repository, "get_for_ai_system", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: risk_assessment_service.create_risk_assessment(
            session, RiskAssessmentCreate(ai_system_row_id=row_id), actor_id=None
        ).id,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)
    assert "already has a risk assessment" in str(refused[0])
    with concurrent_sessions() as session:
        assert count(session, RiskAssessment) == 1
        # The sheet is created before the assessment, so the refused request
        # has to take its sheet back down with it.
        assert count(session, Sheet, Sheet.entity_type == "RiskAssessment") == 1


def test_two_simultaneous_impact_assessments_leave_one(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id

    pause_after(monkeypatch, impact_assessment_repository, "list_for_ai_system", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: impact_assessment_service.create_for_ai_system(
            session, row_id, ImpactAssessmentCreate(), actor_id=None
        ).id,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)
    assert "already has an impact assessment" in str(refused[0])
    with concurrent_sessions() as session:
        assert count(session, ImpactAssessment) == 1


def test_two_simultaneous_assignments_respect_the_cap(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    role = caigo_role(setup_session)
    assert role.max_holders == 1
    # Plain ints, not the ORM objects: setup_session belongs to this thread,
    # and reading an attribute off it from inside the race would be a third
    # session in play on top of the two the test is actually about.
    role_id = role.id
    candidates = [
        make_admin(setup_session, "first@example.com").id,
        make_admin(setup_session, "second@example.com").id,
    ]

    pause_after(monkeypatch, governance_role_repository, "count_holders", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, index: governance_role_service.assign_user(
            session, role_id, candidates[index], actor_id=None
        ).id,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)
    assert "maximum of 1 holder(s)" in str(refused[0])
    with concurrent_sessions() as session:
        assert count(session, GovernanceRoleAssignment) == 1


def test_two_simultaneous_delegations_leave_one_stand_in(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    role = caigo_role(setup_session)
    candidates = [
        make_admin(setup_session, "first@example.com").id,
        make_admin(setup_session, "second@example.com").id,
    ]
    ends_at = datetime.now(UTC) + timedelta(days=7)

    pause_after(
        monkeypatch, governance_role_repository, "list_unrevoked_delegations", barrier()
    )
    outcomes = run_together(
        concurrent_sessions,
        lambda session, index: governance_role_service.delegate_caigo(
            session, candidates[index], ends_at, actor_id=None
        ).id,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)
    with concurrent_sessions() as session:
        standing = governance_role_repository.list_unrevoked_delegations(session, role.id)
        assert len(standing) == 1
        # And the app agrees with the table about who that is.
        assert governance_role_service.active_caigo_delegate(session).id in candidates


# ---------- one caller at a time still behaves as it did ----------


def test_a_second_delegation_replaces_the_first(concurrent_sessions, setup_session) -> None:
    role = caigo_role(setup_session)
    first = make_admin(setup_session, "first@example.com")
    second = make_admin(setup_session, "second@example.com")
    ends_at = datetime.now(UTC) + timedelta(days=7)

    governance_role_service.delegate_caigo(setup_session, first.id, ends_at, actor_id=None)
    governance_role_service.delegate_caigo(setup_session, second.id, ends_at, actor_id=None)

    assert len(governance_role_repository.list_unrevoked_delegations(setup_session, role.id)) == 1
    assert governance_role_service.active_caigo_delegate(setup_session).id == second.id


def test_a_lapsed_delegation_does_not_block_the_next_one(setup_session) -> None:
    """delegate_caigo used to revoke only the delegation active right now, so
    a lapsed one stayed unrevoked forever -- which the unique index would
    read as the role's one standing delegation and refuse to look past."""
    role = caigo_role(setup_session)
    first = make_admin(setup_session, "first@example.com")
    second = make_admin(setup_session, "second@example.com")
    now = datetime.now(UTC)
    setup_session.add(
        GovernanceRoleDelegation(
            governance_role_id=role.id,
            delegate_user_id=first.id,
            starts_at=now - timedelta(days=14),
            ends_at=now - timedelta(days=7),
        )
    )
    setup_session.commit()

    governance_role_service.delegate_caigo(
        setup_session, second.id, now + timedelta(days=7), actor_id=None
    )

    assert len(governance_role_repository.list_unrevoked_delegations(setup_session, role.id)) == 1
    assert governance_role_service.active_caigo_delegate(setup_session).id == second.id


def test_assigning_past_the_cap_one_at_a_time_still_conflicts(setup_session) -> None:
    role = caigo_role(setup_session)
    first = make_admin(setup_session, "first@example.com")
    second = make_admin(setup_session, "second@example.com")
    governance_role_service.assign_user(setup_session, role.id, first.id, actor_id=None)

    with pytest.raises(ConflictError, match="maximum of 1 holder"):
        governance_role_service.assign_user(setup_session, role.id, second.id, actor_id=None)

    # The refused assignment left nothing behind.
    assert governance_role_repository.count_holders(setup_session, role.id) == 1
