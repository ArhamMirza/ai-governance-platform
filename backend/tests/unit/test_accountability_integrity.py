"""Accountability has to survive the people in it changing.

Someone leaving, a role being tidied away, or a policy being stood down must
not quietly strand records that nobody is then allowed to sign off.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.governance_role_seed_data import DEFAULT_ROLES
from app.models.governance_role import GovernanceRole
from app.models.user import UserRole
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.schemas.user import UserUpdate
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    data_inventory_service,
    governance_role_service,
    policy_service,
    procedure_service,
    user_service,
)


def caigo_role(db: Session) -> GovernanceRole:
    return db.query(GovernanceRole).filter_by(name=DEFAULT_ROLES[0][0]).one()


# ---------- the CAIGO role is load-bearing ----------


def test_the_caigo_role_cannot_be_deleted(db_session: Session) -> None:
    """is_caigo, require_caigo and delegate_caigo all find this role by its
    exact name, so deleting it would block every approval in the app."""
    role = caigo_role(db_session)
    # Reparent the seeded children, so the has-children guard isn't what stops us.
    for child in governance_role_service.list_roles(db_session):
        if child.parent_role_id == role.id:
            governance_role_service.update_role(
                db_session, child.id, None, None, None, True, None, False, actor_id=None
            )

    with pytest.raises(ConflictError):
        governance_role_service.delete_role(db_session, role.id, actor_id=None)


def test_another_role_can_still_be_deleted(db_session: Session) -> None:
    role = governance_role_service.create_role(
        db_session, "Vendor Manager", "Owns vendors.", None, None, actor_id=None
    )

    governance_role_service.delete_role(db_session, role.id, actor_id=None)

    names = {r.name for r in governance_role_service.list_roles(db_session)}
    assert "Vendor Manager" not in names


# ---------- a policy can't be stood down under its procedures ----------


def test_a_policy_with_live_procedures_cannot_be_retired(db_session: Session) -> None:
    policy = policy_service.create_policy(
        db_session, PolicyCreate(title="Vendor AI Risk Policy"), actor_id=None
    )
    policy_service.submit_for_review(db_session, policy.id, actor_id=None)
    policy_service.approve_policy(db_session, policy.id, actor_id=None)
    procedure_service.create_procedure(
        db_session,
        ProcedureCreate(title="Vendor Review Procedure", policy_id=policy.id),
        actor_id=None,
    )

    with pytest.raises(ConflictError) as exc:
        policy_service.retire_policy(db_session, policy.id, actor_id=None)

    assert "Vendor Review Procedure" in str(exc.value)


def test_retiring_the_procedures_first_frees_the_policy(db_session: Session) -> None:
    policy = policy_service.create_policy(
        db_session, PolicyCreate(title="Vendor AI Risk Policy"), actor_id=None
    )
    policy_service.submit_for_review(db_session, policy.id, actor_id=None)
    policy_service.approve_policy(db_session, policy.id, actor_id=None)
    procedure = procedure_service.create_procedure(
        db_session,
        ProcedureCreate(title="Vendor Review Procedure", policy_id=policy.id),
        actor_id=None,
    )
    procedure_service.submit_for_review(db_session, procedure.id, actor_id=None)
    procedure_service.approve_procedure(db_session, procedure.id, actor_id=None)
    procedure_service.retire_procedure(db_session, procedure.id, actor_id=None)

    retired = policy_service.retire_policy(db_session, policy.id, actor_id=None)

    assert retired.status == "retired"


def test_a_policy_with_no_procedures_retires_freely(db_session: Session) -> None:
    policy = policy_service.create_policy(
        db_session, PolicyCreate(title="Standalone Policy"), actor_id=None
    )
    policy_service.submit_for_review(db_session, policy.id, actor_id=None)
    policy_service.approve_policy(db_session, policy.id, actor_id=None)

    assert policy_service.retire_policy(db_session, policy.id, actor_id=None).status == "retired"


# ---------- a deactivated owner is surfaced, not silently stuck ----------


def test_accountabilities_report_what_a_user_owns(db_session: Session, make_user) -> None:
    owner = make_user()
    row = ai_system_inventory_service.add_row(
        db_session, {"name": "Resume Screener"}, actor_id=None
    )
    ai_system_lifecycle_service.set_owner(db_session, row.id, owner_id=owner.id, actor_id=None)
    data_inventory_service.add_row(
        db_session,
        {"dataset_name": "Applicant CVs", "data_owner": str(owner.id)},
        actor_id=None,
    )
    governance_role_service.assign_user(
        db_session, caigo_role(db_session).id, owner.id, actor_id=None
    )

    report = user_service.get_accountabilities(db_session, owner.id)

    assert report.ai_systems_owned == ["Resume Screener"]
    assert report.datasets_owned == ["Applicant CVs"]
    assert "Chief AI Governance Officer" in report.governance_roles


def test_accountabilities_are_empty_for_someone_who_owns_nothing(
    db_session: Session, make_user
) -> None:
    report = user_service.get_accountabilities(db_session, make_user().id)

    assert report.is_empty


def test_deactivating_an_owner_is_allowed(db_session: Session, make_user) -> None:
    """Cutting off access can't wait on reassignment -- the point is that it
    becomes visible, not that it becomes impossible."""
    owner = make_user()
    admin = make_user(role=UserRole.ADMIN)
    row = ai_system_inventory_service.add_row(db_session, {"name": "Screener"}, actor_id=None)
    ai_system_lifecycle_service.set_owner(db_session, row.id, owner_id=owner.id, actor_id=None)

    updated = user_service.update_user(
        db_session, owner.id, UserUpdate(is_active=False), actor_id=admin.id
    )

    assert updated.is_active is False
