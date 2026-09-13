"""Two approvers, or two submitters, racing the same record.

Before claim_transition, the read-check-write was as unguarded here as
anywhere else: two callers could both find a record pending, both pass
every gate, and both write -- the second commit simply landing on top of
the first. What should happen instead: exactly one write lands, and the
loser gets a clean conflict rather than silently overwriting the winner's
approval.
"""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidStatusTransitionError
from app.core.security import hash_password
from app.models.policy import PolicyStatus
from app.models.user import User, UserRole
from app.repositories import ai_system_lifecycle_repository, policy_repository
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    data_inventory_service,
    governance_role_service,
    policy_service,
    procedure_service,
)
from tests.concurrency.conftest import barrier, errors, pause_after, run_together
from tests.helpers import complete_impact_assessment_db


def make_user(session: Session, email: str) -> User:
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


def make_caigo(session: Session, email: str) -> User:
    user = make_user(session, email)
    role = governance_role_service.get_role(session, _caigo_role_id(session))
    governance_role_service.assign_user(session, role.id, user.id, actor_id=None)
    return user


def _caigo_role_id(session: Session) -> int:
    from app.core.governance_role_seed_data import DEFAULT_ROLES
    from app.models.governance_role import GovernanceRole

    return session.query(GovernanceRole).filter_by(name=DEFAULT_ROLES[0][0]).one().id


# ---------- two approvers, one record ----------


def test_two_caigo_approvals_of_one_policy_leave_one_approver(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    # One real CAIGO holder (the role caps at one) acting from two threads at
    # once -- what this demonstrates is the same class of race the earlier
    # concurrency PR fixed for role assignment, here for the approval itself.
    approver_id = make_caigo(setup_session, "approver@example.com").id
    policy = policy_service.create_policy(
        setup_session, PolicyCreate(title="Retention Policy"), actor_id=None
    )
    policy_service.submit_for_review(setup_session, policy.id, actor_id=None)
    policy_id = policy.id

    pause_after(monkeypatch, policy_repository, "get", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: policy_service.approve_policy(
            session, policy_id, actor_id=approver_id
        ).status,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], InvalidStatusTransitionError)
    with concurrent_sessions() as session:
        policy = policy_repository.get(session, policy_id)
        assert policy.status == PolicyStatus.APPROVED


def test_two_simultaneous_submissions_leave_one_submitter_of_record(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    """Whichever submission lands, the *other* one can still approve it --
    two audit entries would let the earlier submitter approve their own
    work, which is exactly what require_different_approver exists to stop."""
    from app.repositories import procedure_repository

    procedure = procedure_service.create_procedure(
        setup_session, ProcedureCreate(title="Incident Response"), actor_id=None
    )
    procedure_id = procedure.id
    submitters = [101, 102]

    pause_after(monkeypatch, procedure_repository, "get", barrier())
    outcomes = run_together(
        concurrent_sessions,
        lambda session, index: procedure_service.submit_for_review(
            session, procedure_id, actor_id=submitters[index]
        ).status,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], InvalidStatusTransitionError)

    with concurrent_sessions() as session:
        from app.repositories import audit_log_repository

        submissions = audit_log_repository.list_for_entity(
            session, "Procedure", procedure_id, ["submitted_for_review"]
        )
        assert len(submissions) == 1


def test_two_simultaneous_deployment_approvals_leave_one_approver(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    # A real CAIGO holder: require_caigo isn't a no-op here, unlike actor_id=None
    # elsewhere in this file, so approve_deployment needs an actual approver to
    # authorize as. Both threads act as the same one -- what this demonstrates
    # is the double-approval, whether that is one person's double-click or two
    # people sharing an identity, not a segregation-of-duties race.
    approver_id = make_caigo(setup_session, "approver@example.com").id
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id
    ai_system_lifecycle_service.set_deployment_record(
        setup_session,
        row_id,
        environment="prod",
        version="1.0",
        deployed_at=date.today(),
        actor_id=None,
    )
    setup_session.commit()

    pause_after(
        monkeypatch, ai_system_lifecycle_repository, "get_for_ai_system", barrier()
    )
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: ai_system_lifecycle_service.approve_deployment(
            session, row_id, actor_id=approver_id
        ).deployment_approved_at,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)
    assert "already been approved" in str(refused[0])


def test_approving_a_deployment_twice_in_a_row_is_refused(setup_session) -> None:
    approver_id = make_caigo(setup_session, "approver@example.com").id
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id
    ai_system_lifecycle_service.set_deployment_record(
        setup_session,
        row_id,
        environment="prod",
        version="1.0",
        deployed_at=date.today(),
        actor_id=None,
    )
    ai_system_lifecycle_service.approve_deployment(setup_session, row_id, actor_id=approver_id)

    with pytest.raises(ConflictError, match="already been approved"):
        ai_system_lifecycle_service.approve_deployment(setup_session, row_id, actor_id=approver_id)


def test_two_simultaneous_dataset_approvals_leave_one_approver(
    concurrent_sessions, setup_session, monkeypatch
) -> None:
    from app.repositories import data_inventory_record_repository

    row = data_inventory_service.add_row(
        setup_session, {"dataset_name": "Applicant CVs"}, actor_id=None
    )
    data_inventory_service.update_row(setup_session, row.id, {"data_owner": "1"}, actor_id=None)
    data_inventory_service.submit_for_approval(setup_session, row.id, actor_id=None)
    row_id = row.id

    pause_after(
        monkeypatch, data_inventory_record_repository, "get_for_row", barrier()
    )
    outcomes = run_together(
        concurrent_sessions,
        lambda session, _: data_inventory_service.approve(session, row_id, actor_id=None).status,
    )

    refused = list(errors(outcomes))
    assert len(refused) == 1
    assert isinstance(refused[0], ConflictError)


def test_an_approved_assessment_survives_treating_a_risk_item_but_not_editing_it(
    setup_session,
) -> None:
    """Not a race -- a sequential regression making sure claim_transition's
    guard didn't change what withdrawal is supposed to do."""
    from app.schemas.risk_assessment import RiskAssessmentCreate
    from app.services import risk_assessment_service

    make_user(setup_session, "owner@example.com")  # _ensure_owner needs a real user to assign
    row_id = ai_system_inventory_service.add_row(
        setup_session, {"name": "Resume Screener"}, actor_id=None
    ).id
    complete_impact_assessment_db(setup_session, row_id)
    assessment = risk_assessment_service.create_risk_assessment(
        setup_session, RiskAssessmentCreate(ai_system_row_id=row_id), actor_id=None
    )
    item = risk_assessment_service.add_row(
        setup_session, assessment.id, {"category": "Bias", "status": "open"}, actor_id=None
    )
    risk_assessment_service.submit_for_owner_approval(
        setup_session, assessment.id, actor_id=None
    )
    risk_assessment_service.approve_owner_stage(setup_session, assessment.id, actor_id=None)
    risk_assessment_service.approve_caigo_stage(setup_session, assessment.id, actor_id=None)

    risk_assessment_service.update_row(
        setup_session, assessment.id, item.id, {"status": "closed"}, actor_id=None
    )
    still_approved = risk_assessment_service.get_risk_assessment(setup_session, assessment.id)
    assert still_approved.status == "completed"

    risk_assessment_service.update_row(
        setup_session, assessment.id, item.id, {"mitigation": "Retrained the model"}, actor_id=None
    )
    reverted = risk_assessment_service.get_risk_assessment(setup_session, assessment.id)
    assert reverted.status == "draft"
