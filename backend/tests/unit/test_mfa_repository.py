"""The statements that must be atomic: spending a code or a step is one
UPDATE that says whether it won, so two requests can't both succeed."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.mfa import MFARecoveryCode, UserMFA
from app.models.user import User, UserRole
from app.repositories import mfa_repository


def with_mfa(db: Session, user: User, *, confirmed: bool = True) -> UserMFA:
    mfa = UserMFA(user_id=user.id, secret_encrypted="x", confirmed=confirmed)
    db.add(mfa)
    db.commit()
    return mfa


# ---------- a time step is spent once ----------


def test_the_first_use_of_a_step_wins(db_session: Session, test_user: User) -> None:
    mfa = with_mfa(db_session, test_user)

    assert mfa_repository.advance_step(db_session, mfa.id, 100) is True
    db_session.refresh(mfa)
    assert mfa.last_used_step == 100


def test_the_same_step_cannot_be_spent_twice(db_session: Session, test_user: User) -> None:
    mfa = with_mfa(db_session, test_user)
    mfa_repository.advance_step(db_session, mfa.id, 100)

    assert mfa_repository.advance_step(db_session, mfa.id, 100) is False


def test_an_earlier_step_cannot_be_spent_after_a_later_one(
    db_session: Session, test_user: User
) -> None:
    mfa = with_mfa(db_session, test_user)
    mfa_repository.advance_step(db_session, mfa.id, 100)

    assert mfa_repository.advance_step(db_session, mfa.id, 99) is False
    db_session.refresh(mfa)
    assert mfa.last_used_step == 100


def test_a_later_step_can_be_spent(db_session: Session, test_user: User) -> None:
    mfa = with_mfa(db_session, test_user)
    mfa_repository.advance_step(db_session, mfa.id, 100)

    assert mfa_repository.advance_step(db_session, mfa.id, 101) is True


def test_a_step_is_spent_against_the_right_account_only(
    db_session: Session, test_user: User, second_user: User
) -> None:
    first = with_mfa(db_session, test_user)
    second = with_mfa(db_session, second_user)
    mfa_repository.advance_step(db_session, first.id, 100)

    assert mfa_repository.advance_step(db_session, second.id, 100) is True


# ---------- a recovery code is spent once ----------


def codes(db: Session, user: User, *hashes: str) -> None:
    mfa_repository.replace_recovery_codes(db, user.id, list(hashes))


def test_a_recovery_code_works_once(db_session: Session, test_user: User) -> None:
    codes(db_session, test_user, "aaa", "bbb")

    assert mfa_repository.use_recovery_code(db_session, test_user.id, "aaa") is True
    assert mfa_repository.use_recovery_code(db_session, test_user.id, "aaa") is False
    assert mfa_repository.unused_recovery_codes(db_session, test_user.id) == 1


def test_an_unknown_code_is_refused(db_session: Session, test_user: User) -> None:
    codes(db_session, test_user, "aaa")

    assert mfa_repository.use_recovery_code(db_session, test_user.id, "zzz") is False
    assert mfa_repository.unused_recovery_codes(db_session, test_user.id) == 1


def test_one_persons_code_is_no_use_to_another(
    db_session: Session, test_user: User, second_user: User
) -> None:
    codes(db_session, test_user, "aaa")

    assert mfa_repository.use_recovery_code(db_session, second_user.id, "aaa") is False
    assert mfa_repository.unused_recovery_codes(db_session, test_user.id) == 1


def test_replacing_the_codes_drops_the_old_ones_and_resets_the_count(
    db_session: Session, test_user: User
) -> None:
    codes(db_session, test_user, "aaa", "bbb", "ccc")
    mfa_repository.use_recovery_code(db_session, test_user.id, "aaa")

    codes(db_session, test_user, "ddd")

    assert mfa_repository.use_recovery_code(db_session, test_user.id, "bbb") is False
    assert mfa_repository.unused_recovery_codes(db_session, test_user.id) == 1
    assert db_session.query(MFARecoveryCode).filter_by(user_id=test_user.id).count() == 1


def test_deleting_removes_the_authenticator_and_every_code(
    db_session: Session, test_user: User
) -> None:
    with_mfa(db_session, test_user)
    codes(db_session, test_user, "aaa", "bbb")

    mfa_repository.delete_for_user(db_session, test_user.id)

    assert mfa_repository.get(db_session, test_user.id) is None
    assert db_session.query(MFARecoveryCode).count() == 0


# ---------- who the organization rule would catch ----------


def test_only_active_administrators_without_it_are_counted(
    db_session: Session, make_user: Callable[..., User]
) -> None:
    has_it = make_user(role=UserRole.ADMIN)
    with_mfa(db_session, has_it)
    unfinished = make_user(role=UserRole.ADMIN)
    with_mfa(db_session, unfinished, confirmed=False)
    make_user(role=UserRole.ADMIN)  # counted
    make_user(role=UserRole.ADMIN, is_active=False)  # deactivated: not counted
    make_user(role=UserRole.CONTRIBUTOR)  # not an administrator
    make_user(role=UserRole.EMPLOYEE)

    # `unfinished` has started setting up but is not protected yet, so is counted too.
    assert mfa_repository.count_admins_without_mfa(db_session) == 2
