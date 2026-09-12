from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.user import UserRole
from app.services import governance_role_service


def get_role_id(db: Session, name: str) -> int:
    return next(r.id for r in governance_role_service.list_roles(db) if r.name == name)


def test_seeded_roles_report_to_caigo(db_session: Session) -> None:
    roles = governance_role_service.list_roles(db_session)
    by_name = {r.name: r for r in roles}

    caigo = by_name["Chief AI Governance Officer"]
    assert caigo.parent_role_id is None
    assert caigo.max_holders == 1
    for name in ("Data Owner", "AI System Owner", "Risk Owner", "Implementation Team"):
        assert by_name[name].parent_role_id == caigo.id
        assert by_name[name].max_holders is None


def test_assigning_caigo_requires_an_admin_account(db_session: Session, make_user) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    viewer = make_user(role=UserRole.VIEWER)

    with pytest.raises(ValidationError):
        governance_role_service.assign_user(db_session, caigo_id, viewer.id, actor_id=None)


def test_assigning_caigo_succeeds_for_an_admin(db_session: Session, make_user) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    admin = make_user(role=UserRole.ADMIN)

    governance_role_service.assign_user(db_session, caigo_id, admin.id, actor_id=None)

    holders = governance_role_service.holders_for_role(db_session, caigo_id)
    assert [h.id for h in holders] == [admin.id]


def test_caigo_is_capped_at_one_holder(db_session: Session, make_user) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    first_admin = make_user(role=UserRole.ADMIN)
    second_admin = make_user(role=UserRole.ADMIN)
    governance_role_service.assign_user(db_session, caigo_id, first_admin.id, actor_id=None)

    with pytest.raises(ConflictError):
        governance_role_service.assign_user(db_session, caigo_id, second_admin.id, actor_id=None)


def test_a_role_without_a_cap_accepts_multiple_holders(db_session: Session, make_user) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    first = make_user()
    second = make_user()

    governance_role_service.assign_user(db_session, risk_owner_id, first.id, actor_id=None)
    governance_role_service.assign_user(db_session, risk_owner_id, second.id, actor_id=None)

    holders = governance_role_service.holders_for_role(db_session, risk_owner_id)
    assert {h.id for h in holders} == {first.id, second.id}


def test_assigning_the_same_user_twice_is_rejected(db_session: Session, make_user) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    user = make_user()
    governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)

    with pytest.raises(ConflictError):
        governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)


def test_unassign_removes_the_holder(db_session: Session, make_user) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    user = make_user()
    governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)

    governance_role_service.unassign_user(db_session, risk_owner_id, user.id, actor_id=None)

    assert governance_role_service.holders_for_role(db_session, risk_owner_id) == []


def test_a_user_can_hold_more_than_one_role(db_session: Session, make_user) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    ai_system_owner_id = get_role_id(db_session, "AI System Owner")
    user = make_user()

    governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)
    governance_role_service.assign_user(db_session, ai_system_owner_id, user.id, actor_id=None)

    names = {r.name for r in governance_role_service.list_roles_for_user(db_session, user.id)}
    assert names == {"Risk Owner", "AI System Owner"}


def test_role_names_by_user_covers_every_holder(db_session: Session, make_user) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    user = make_user()
    governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)

    badges = governance_role_service.role_names_by_user(db_session)

    assert badges[user.id] == ["Risk Owner"]


def test_create_role_rejects_a_duplicate_name(db_session: Session) -> None:
    with pytest.raises(ConflictError):
        governance_role_service.create_role(
            db_session, "Risk Owner", "Duplicate.", None, None, actor_id=None
        )


def test_create_role_with_a_parent_reports_correctly(db_session: Session) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")

    role = governance_role_service.create_role(
        db_session, "Vendor Manager", "Owns third-party AI vendor relationships.",
        caigo_id, None, actor_id=None,
    )

    assert role.parent_role_id == caigo_id


def test_update_role_can_reparent(db_session: Session) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    data_owner_id = get_role_id(db_session, "Data Owner")

    updated = governance_role_service.update_role(
        db_session, risk_owner_id, None, None, data_owner_id, True, None, False, actor_id=None,
    )

    assert updated.parent_role_id == data_owner_id


def test_a_role_cannot_report_to_itself(db_session: Session) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")

    with pytest.raises(ValidationError):
        governance_role_service.update_role(
            db_session, risk_owner_id, None, None, risk_owner_id, True, None, False, actor_id=None,
        )


def test_a_role_cannot_be_reparented_under_its_own_descendant(db_session: Session) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    # Risk Owner already reports to CAIGO; reparenting CAIGO under Risk Owner
    # would make CAIGO its own grandchild.
    with pytest.raises(ValidationError):
        governance_role_service.update_role(
            db_session, caigo_id, None, None, risk_owner_id, True, None, False, actor_id=None,
        )


def test_cannot_cap_a_role_below_its_current_holder_count(
    db_session: Session, make_user
) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    governance_role_service.assign_user(db_session, risk_owner_id, make_user().id, actor_id=None)
    governance_role_service.assign_user(db_session, risk_owner_id, make_user().id, actor_id=None)

    with pytest.raises(ValidationError):
        governance_role_service.update_role(
            db_session, risk_owner_id, None, None, None, False, 1, True, actor_id=None,
        )


def test_delete_is_blocked_while_a_role_has_children(db_session: Session) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")

    with pytest.raises(ConflictError):
        governance_role_service.delete_role(db_session, caigo_id, actor_id=None)


def test_delete_removes_a_childless_role_and_its_assignments(
    db_session: Session, make_user
) -> None:
    risk_owner_id = get_role_id(db_session, "Risk Owner")
    user = make_user()
    governance_role_service.assign_user(db_session, risk_owner_id, user.id, actor_id=None)

    governance_role_service.delete_role(db_session, risk_owner_id, actor_id=None)

    with pytest.raises(NotFoundError):
        governance_role_service.get_role(db_session, risk_owner_id)
    assert governance_role_service.list_roles_for_user(db_session, user.id) == []


def test_is_caigo_true_only_for_the_actual_holder(db_session: Session, make_user) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    caigo_holder = make_user(role=UserRole.ADMIN)
    other_admin = make_user(role=UserRole.ADMIN)
    governance_role_service.assign_user(db_session, caigo_id, caigo_holder.id, actor_id=None)

    assert governance_role_service.is_caigo(db_session, caigo_holder.id) is True
    assert governance_role_service.is_caigo(db_session, other_admin.id) is False


def test_require_caigo_raises_for_a_non_caigo_admin(db_session: Session, make_user) -> None:
    admin = make_user(role=UserRole.ADMIN)

    with pytest.raises(AuthorizationError):
        governance_role_service.require_caigo(db_session, admin.id)


def test_require_caigo_is_a_noop_with_no_real_actor(db_session: Session) -> None:
    governance_role_service.require_caigo(db_session, None)


def test_vacant_roles_lists_only_roles_with_no_holders(db_session: Session, make_user) -> None:
    caigo_id = get_role_id(db_session, "Chief AI Governance Officer")
    governance_role_service.assign_user(
        db_session, caigo_id, make_user(role=UserRole.ADMIN).id, actor_id=None
    )

    vacant_names = {role.name for role in governance_role_service.vacant_roles(db_session)}

    assert "Chief AI Governance Officer" not in vacant_names
    assert vacant_names == {"Data Owner", "AI System Owner", "Risk Owner", "Implementation Team"}


def test_vacant_roles_empty_once_every_role_is_held(db_session: Session, make_user) -> None:
    for role in governance_role_service.list_roles(db_session):
        user = make_user(role=UserRole.ADMIN)
        governance_role_service.assign_user(db_session, role.id, user.id, actor_id=None)

    assert governance_role_service.vacant_roles(db_session) == []


def test_delegating_caigo_requires_an_admin_account(db_session: Session, make_user) -> None:
    viewer = make_user(role=UserRole.VIEWER)

    with pytest.raises(ValidationError):
        governance_role_service.delegate_caigo(
            db_session, viewer.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
        )


def test_delegating_caigo_rejects_an_end_time_in_the_past(
    db_session: Session, make_user
) -> None:
    admin = make_user(role=UserRole.ADMIN)

    with pytest.raises(ValidationError):
        governance_role_service.delegate_caigo(
            db_session, admin.id, datetime.now(UTC) - timedelta(days=1), actor_id=None
        )


def test_is_caigo_true_for_an_active_delegate(db_session: Session, make_user) -> None:
    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )

    assert governance_role_service.is_caigo(db_session, delegate.id) is True


def test_is_caigo_false_once_the_delegation_has_expired(
    db_session: Session, make_user
) -> None:
    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(seconds=1), actor_id=None
    )
    delegation = governance_role_service.get_caigo_delegation(db_session)
    # Backdate it rather than sleeping the test past the real clock.
    delegation.starts_at = datetime.now(UTC) - timedelta(days=2)
    delegation.ends_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()

    assert governance_role_service.is_caigo(db_session, delegate.id) is False


def test_is_caigo_false_after_the_delegation_is_revoked(
    db_session: Session, make_user
) -> None:
    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )

    governance_role_service.revoke_caigo_delegation(db_session, actor_id=None)

    assert governance_role_service.is_caigo(db_session, delegate.id) is False


def test_revoking_with_no_active_delegation_is_rejected(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        governance_role_service.revoke_caigo_delegation(db_session, actor_id=None)


def test_setting_a_new_delegation_revokes_the_old_one(db_session: Session, make_user) -> None:
    first = make_user(role=UserRole.ADMIN)
    second = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, first.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )

    governance_role_service.delegate_caigo(
        db_session, second.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )

    assert governance_role_service.is_caigo(db_session, first.id) is False
    assert governance_role_service.is_caigo(db_session, second.id) is True


def test_role_names_by_user_badges_the_active_delegate(
    db_session: Session, make_user
) -> None:
    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )

    badges = governance_role_service.role_names_by_user(db_session)

    assert badges[delegate.id] == ["Chief AI Governance Officer"]
