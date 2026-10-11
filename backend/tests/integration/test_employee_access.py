"""The employee login: a restricted account that reaches only the employee home.

The point of most of these tests is what an employee *can't* do -- a platform
full of risk assessments and incident records shouldn't open up because
someone was given a login to report a concern.
"""

import re
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.policy import PolicyStatus
from app.models.procedure import ProcedureStatus
from app.models.user import User, UserRole
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.services import policy_service, procedure_service

# The routes an employee login is for. Everything else under /api/v1 must refuse it.
EMPLOYEE_PREFIXES = ("/api/v1/auth/", "/api/v1/health", "/api/v1/staff/")


def upload(client: TestClient, entity_type: str, entity_id: int, filename: str = "policy.pdf"):
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": entity_type, "entity_id": str(entity_id)},
        files={"file": (filename, b"policy-bytes", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_policy(db: Session, title: str, *, status: str, shared: bool):
    policy = policy_service.create_policy(db, PolicyCreate(title=title), actor_id=None)
    policy.status = status
    policy.shared_with_employees = shared
    db.commit()
    return policy


def make_procedure(db: Session, title: str, *, status: str, shared: bool):
    procedure = procedure_service.create_procedure(db, ProcedureCreate(title=title), actor_id=None)
    procedure.status = status
    procedure.shared_with_employees = shared
    db.commit()
    return procedure


def test_an_employee_is_refused_every_route_outside_the_staff_portal(
    client: TestClient, make_user: Callable[..., User], login_as
) -> None:
    """Walks every route in the app, so a router added later without the
    shared dependency fails here instead of quietly opening up."""
    login_as(make_user(role=UserRole.EMPLOYEE))
    checked = 0
    not_refused = []
    # The OpenAPI schema lists every path and method however the routers
    # were included, so no route can be missed by how it was mounted.
    for route_path, operations in app.openapi()["paths"].items():
        if route_path.startswith(EMPLOYEE_PREFIXES):
            continue
        path = re.sub(r"\{[^}]+\}", "1", route_path)
        for method in sorted(operations):
            body = {} if method in ("post", "put", "patch") else None
            response = client.request(method.upper(), path, json=body)
            checked += 1
            if response.status_code != 403:
                not_refused.append((method.upper(), route_path, response.status_code))

    assert checked > 150, "the walk should cover the whole API"
    assert not_refused == []


def test_internal_roles_are_unaffected(
    client: TestClient, make_user: Callable[..., User], login_as
) -> None:
    for role in (UserRole.ADMIN, UserRole.CONTRIBUTOR, UserRole.VIEWER):
        login_as(make_user(role=role))
        assert client.get("/api/v1/policies").status_code == 200, role
        assert client.get("/api/v1/dashboard/summary").status_code == 200, role


def test_an_employee_can_still_ask_who_they_are(
    client: TestClient, make_user: Callable[..., User], login_as
) -> None:
    employee = make_user(role=UserRole.EMPLOYEE, name="Elena Employee")
    login_as(employee)

    body = client.get("/api/v1/auth/me").json()

    assert (body["name"], body["role"]) == ("Elena Employee", "employee")


def test_an_employee_holds_no_permission(make_user: Callable[..., User]) -> None:
    from app.core.permissions import Action, has_permission

    assert not any(has_permission(UserRole.EMPLOYEE, action) for action in Action)


def test_the_library_lists_only_approved_policies_and_procedures_that_are_shared(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    make_policy(db_session, "Shared and approved", status=PolicyStatus.APPROVED, shared=True)
    make_policy(db_session, "Approved, not shared", status=PolicyStatus.APPROVED, shared=False)
    make_policy(db_session, "Shared draft", status=PolicyStatus.DRAFT, shared=True)
    make_policy(db_session, "Shared, in review", status=PolicyStatus.IN_REVIEW, shared=True)
    make_policy(db_session, "Shared but retired", status=PolicyStatus.RETIRED, shared=True)
    make_procedure(db_session, "Shared procedure", status=ProcedureStatus.APPROVED, shared=True)
    make_procedure(db_session, "Procedure in draft", status=ProcedureStatus.DRAFT, shared=True)
    login_as(make_user(role=UserRole.EMPLOYEE))

    library = client.get("/api/v1/staff/library").json()

    assert [(i["kind"], i["title"]) for i in library] == [
        ("policy", "Shared and approved"),
        ("procedure", "Shared procedure"),
    ]


def test_a_library_item_carries_only_what_an_employee_needs(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    make_policy(db_session, "AI acceptable use", status=PolicyStatus.APPROVED, shared=True)
    login_as(make_user(role=UserRole.EMPLOYEE))

    item = client.get("/api/v1/staff/library").json()[0]

    # No owner, review dates, status or tags: an allowlist, not "the record
    # minus a few fields".
    assert set(item) == {
        "kind",
        "id",
        "title",
        "description",
        "version",
        "effective_date",
        "documents",
    }


def test_an_employee_can_download_a_document_of_a_shared_policy(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    policy = make_policy(db_session, "Shared", status=PolicyStatus.APPROVED, shared=True)
    document = upload(client, "Policy", policy.id)
    login_as(make_user(role=UserRole.EMPLOYEE))

    listed = client.get("/api/v1/staff/library").json()[0]["documents"]
    response = client.get(f"/api/v1/staff/library/documents/{document['id']}")

    assert [d["filename"] for d in listed] == ["policy.pdf"]
    assert response.status_code == 200
    assert response.content == b"policy-bytes"


def test_a_document_of_a_shared_procedure_can_be_downloaded_too(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    procedure = make_procedure(db_session, "Shared", status=ProcedureStatus.APPROVED, shared=True)
    document = upload(client, "Procedure", procedure.id, "steps.pdf")
    login_as(make_user(role=UserRole.EMPLOYEE))

    assert client.get(f"/api/v1/staff/library/documents/{document['id']}").status_code == 200


def test_everything_else_is_not_found_rather_than_forbidden(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    unshared = make_policy(db_session, "Unshared", status=PolicyStatus.APPROVED, shared=False)
    draft = make_policy(db_session, "Draft", status=PolicyStatus.DRAFT, shared=True)
    retired = make_policy(db_session, "Retired", status=PolicyStatus.RETIRED, shared=True)
    ids = [
        upload(client, "Policy", unshared.id)["id"],
        upload(client, "Policy", draft.id)["id"],
        upload(client, "Policy", retired.id)["id"],
        # Not a policy or procedure at all.
        upload(client, "AISystem", 1, "risk-notes.pdf")["id"],
        upload(client, "Supplier", 1, "contract.pdf")["id"],
        99999,
    ]
    login_as(make_user(role=UserRole.EMPLOYEE))

    statuses = [client.get(f"/api/v1/staff/library/documents/{i}").status_code for i in ids]

    # The same answer whether it doesn't exist or just isn't theirs.
    assert statuses == [404] * len(ids)


def test_the_general_evidence_download_stays_internal(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    policy = make_policy(db_session, "Shared", status=PolicyStatus.APPROVED, shared=True)
    document = upload(client, "Policy", policy.id)
    login_as(make_user(role=UserRole.EMPLOYEE))

    assert client.get(f"/api/v1/evidence/{document['id']}/download").status_code == 403


def test_sharing_is_set_by_someone_who_can_edit_and_leaves_the_approval_alone(
    client: TestClient, db_session: Session, make_user: Callable[..., User], login_as
) -> None:
    policy = make_policy(db_session, "AI policy", status=PolicyStatus.APPROVED, shared=False)
    procedure = make_procedure(
        db_session, "Escalation", status=ProcedureStatus.APPROVED, shared=False
    )

    login_as(make_user(role=UserRole.VIEWER))
    assert (
        client.put(
            f"/api/v1/policies/{policy.id}/sharing", json={"shared_with_employees": True}
        ).status_code
        == 403
    )

    login_as(make_user(role=UserRole.CONTRIBUTOR))
    shared_policy = client.put(
        f"/api/v1/policies/{policy.id}/sharing", json={"shared_with_employees": True}
    )
    shared_procedure = client.put(
        f"/api/v1/procedures/{procedure.id}/sharing", json={"shared_with_employees": True}
    )

    assert shared_policy.status_code == 200, shared_policy.text
    # Who can read it isn't what it says, so approval stands.
    assert (shared_policy.json()["status"], shared_policy.json()["shared_with_employees"]) == (
        "approved",
        True,
    )
    assert (
        shared_procedure.json()["status"],
        shared_procedure.json()["shared_with_employees"],
    ) == (
        "approved",
        True,
    )

    unshared = client.put(
        f"/api/v1/policies/{policy.id}/sharing", json={"shared_with_employees": False}
    )
    assert unshared.json()["shared_with_employees"] is False


def test_changing_who_a_policy_is_shared_with_is_audit_logged(
    client: TestClient, db_session: Session
) -> None:
    from app.models.audit_log import AuditLogEntry

    policy = make_policy(db_session, "AI policy", status=PolicyStatus.APPROVED, shared=False)

    client.put(f"/api/v1/policies/{policy.id}/sharing", json={"shared_with_employees": True})

    entry = (
        db_session.query(AuditLogEntry)
        .filter_by(entity_type="Policy", entity_id=policy.id, action="sharing_updated")
        .one()
    )
    assert entry.diff == {"shared_with_employees": True}
