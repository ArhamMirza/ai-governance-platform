"""The register of third-party AI tools employees may use, and the requests
to add to it.

Which tools are allowed is a governance decision, so approving, restricting
or revoking one goes through the Chief AI Governance Officer
(governance_role_service.require_caigo) -- editing the catalogue is ordinary
edit permission. An employee asks for a tool with a request; approving the
request approves the tool, so the two can't disagree. Whether an approved
tool is past its review is computed live, never stored.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import ai_tool_catalog_data, ai_tool_domains, review_cadence
from app.core.exceptions import (
    ConflictError,
    InvalidStatusTransitionError,
    NotFoundError,
    ValidationError,
)
from app.models.ai_tool import (
    AITool,
    AIToolRequest,
    AIToolRequestStatus,
    AIToolStatus,
)
from app.repositories import ai_tool_repository, supplier_repository
from app.schemas.ai_tool import (
    AIToolCreate,
    AIToolDecision,
    AIToolRequestCreate,
    AIToolRequestDecision,
    AIToolUpdate,
)
from app.services import audit_service, framework_service, governance_role_service

ENTITY_TYPE = "AITool"
REQUEST_ENTITY_TYPE = "AIToolRequest"

# What is on offer to employees.
ALLOWED_STATUSES = frozenset({AIToolStatus.APPROVED, AIToolStatus.RESTRICTED})


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


def review_overdue(tool: AITool, today: date | None = None) -> bool:
    return tool.status in ALLOWED_STATUSES and review_cadence.is_review_overdue(
        tool.review_due, _today(today)
    )


def _get_or_raise(db: Session, tool_id: int) -> AITool:
    tool = ai_tool_repository.get(db, tool_id)
    if tool is None:
        raise NotFoundError("AITool", tool_id)
    return tool


def _normalise_domains(domains: list[str]) -> list[str]:
    """Bare, lower-case, de-duplicated, in the order given."""
    seen: dict[str, None] = {}
    for domain in domains:
        seen.setdefault(ai_tool_domains.normalize_domain(domain), None)
    return list(seen)


def _check_domains_free(db: Session, domains: list[str], own_id: int | None) -> None:
    """A domain belongs to one tool: two tools claiming it would leave the
    browser unable to say which one a visit is to."""
    for other in ai_tool_repository.list_all(db):
        if other.id == own_id:
            continue
        clash = set(domains) & set(other.domains)
        if clash:
            raise ConflictError(f"{sorted(clash)[0]} already belongs to {other.name}.")


def _check_supplier(db: Session, supplier_id: int | None) -> None:
    if supplier_id is not None and supplier_repository.get(db, supplier_id) is None:
        raise NotFoundError("Supplier", supplier_id)


def list_tools(db: Session) -> list[AITool]:
    return ai_tool_repository.list_all(db)


def get_tool(db: Session, tool_id: int) -> AITool:
    return _get_or_raise(db, tool_id)


def create_tool(db: Session, data: AIToolCreate, actor_id: int | None) -> AITool:
    fields = data.model_dump()
    fields["domains"] = _normalise_domains(data.domains)
    _check_domains_free(db, fields["domains"], None)
    _check_supplier(db, data.supplier_id)
    tool = ai_tool_repository.create(db, AITool(**fields, status=AIToolStatus.CATALOGUED))
    audit_service.log(
        db, ENTITY_TYPE, tool.id, "created", actor_id, {"name": tool.name, "domains": tool.domains}
    )
    return tool


def update_tool(db: Session, tool_id: int, data: AIToolUpdate, actor_id: int | None) -> AITool:
    tool = _get_or_raise(db, tool_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("name", "domains"):
        if required in changes and changes[required] is None:
            raise ValidationError("A tool needs a name and at least one domain.")
    if "domains" in changes:
        changes["domains"] = _normalise_domains(changes["domains"])
        _check_domains_free(db, changes["domains"], tool.id)
    if "supplier_id" in changes:
        _check_supplier(db, changes["supplier_id"])
    for field, value in changes.items():
        setattr(tool, field, value)
    tool = ai_tool_repository.save(db, tool)
    audit_service.log(db, ENTITY_TYPE, tool.id, "updated", actor_id, changes)
    return tool


def decide_tool(
    db: Session,
    tool_id: int,
    data: AIToolDecision,
    actor_id: int | None,
    today: date | None = None,
) -> AITool:
    """The Chief AI Governance Officer approves, restricts or revokes a tool.
    Approving or restricting says what data it may be given and sets the
    review date (a year on by default); revoking needs a reason."""
    governance_role_service.require_caigo(db, actor_id)
    tool = _get_or_raise(db, tool_id)
    reference = _today(today)
    target = {
        "approve": AIToolStatus.APPROVED,
        "restrict": AIToolStatus.RESTRICTED,
        "revoke": AIToolStatus.REVOKED,
    }[data.action]
    note = (data.note or "").strip() or None

    if tool.status == target:
        raise InvalidStatusTransitionError(f"{tool.name} is already {tool.status}.")
    if target == AIToolStatus.REVOKED:
        if tool.status == AIToolStatus.CATALOGUED:
            raise InvalidStatusTransitionError(
                f"{tool.name} was never approved, so there is nothing to revoke."
            )
        if note is None:
            raise ValidationError("Say why access is being withdrawn.")
        tool.review_due = None
    else:
        if data.max_data_classification is None:
            raise ValidationError("Say what is the most sensitive data this tool may be given.")
        tool.max_data_classification = data.max_data_classification
        if data.conditions_of_use is not None:
            tool.conditions_of_use = data.conditions_of_use.strip() or None
        tool.review_due = data.review_due or review_cadence.next_review_date(reference)

    tool.status = target
    tool.decided_by = actor_id
    tool.decided_on = reference
    tool.decision_note = note
    tool = ai_tool_repository.save(db, tool)
    audit_service.log(
        db,
        ENTITY_TYPE,
        tool.id,
        f"decision_{data.action}",
        actor_id,
        {
            "status": tool.status,
            "max_data_classification": tool.max_data_classification,
            "review_due": tool.review_due,
            "note": note,
        },
    )
    return tool


def delete_tool(db: Session, tool_id: int, actor_id: int | None) -> None:
    """Only a catalogued tool nobody has decided on or asked for. Once a tool
    has been approved, or an employee has requested it, it is part of the
    record of what was allowed and why, so it is revoked instead."""
    from app.services import evidence_service

    tool = _get_or_raise(db, tool_id)
    if tool.status != AIToolStatus.CATALOGUED or tool.decided_on is not None:
        raise InvalidStatusTransitionError(
            "This tool has been decided on, so it can't be deleted; revoke it instead."
        )
    if ai_tool_repository.list_requests_for_tool(db, tool_id):
        raise InvalidStatusTransitionError(
            "Employees have requested this tool, so it can't be deleted."
        )
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, tool_id)
    framework_service.delete_tags(db, ENTITY_TYPE, tool_id)
    ai_tool_repository.delete(db, tool)
    audit_service.log(db, ENTITY_TYPE, tool_id, "deleted", actor_id, {"name": tool.name})


def install_default_catalog(db: Session) -> int:
    """Adds the built-in list of well-known AI sites, skipping any whose
    domain is already catalogued. Safe to run again. Returns how many were
    added."""
    taken = {domain for tool in ai_tool_repository.list_all(db) for domain in tool.domains}
    added = 0
    for name, vendor, domains in ai_tool_catalog_data.DEFAULT_CATALOG:
        if taken & set(domains):
            continue
        ai_tool_repository.create(
            db, AITool(name=name, vendor=vendor, domains=domains, status=AIToolStatus.CATALOGUED)
        )
        taken.update(domains)
        added += 1
    return added


def tool_for_host(db: Session, host: str) -> AITool | None:
    """The tool a web address belongs to, if the catalogue knows it."""
    entries = [
        (domain, tool) for tool in ai_tool_repository.list_all(db) for domain in tool.domains
    ]
    return ai_tool_domains.best_match(host.lower(), entries)


# ---------- requests ----------


def _get_request_or_raise(db: Session, request_id: int) -> AIToolRequest:
    request = ai_tool_repository.get_request(db, request_id)
    if request is None:
        raise NotFoundError("AIToolRequest", request_id)
    return request


def list_requests(db: Session) -> list[AIToolRequest]:
    return ai_tool_repository.list_requests(db)


def get_request(db: Session, request_id: int) -> AIToolRequest:
    return _get_request_or_raise(db, request_id)


def list_my_requests(db: Session, requester_id: int) -> list[AIToolRequest]:
    return ai_tool_repository.list_requests_for_requester(db, requester_id)


def create_request(
    db: Session, data: AIToolRequestCreate, requester_id: int, today: date | None = None
) -> AIToolRequest:
    tool_name = data.tool_name.strip()
    domain = ai_tool_domains.normalize_domain(data.domain) if data.domain else None
    if data.tool_id is not None:
        tool = _get_or_raise(db, data.tool_id)
        if tool.status in ALLOWED_STATUSES:
            raise ValidationError(f"{tool.name} is already approved; see the approved tools.")
        tool_name = tool.name
    elif domain is not None:
        known = tool_for_host(db, domain)
        if known is not None and known.status in ALLOWED_STATUSES:
            raise ValidationError(f"{known.name} is already approved; see the approved tools.")
    for open_request in ai_tool_repository.list_requests_for_requester(db, requester_id):
        same_tool = (data.tool_id is not None and open_request.tool_id == data.tool_id) or (
            open_request.tool_name.lower() == tool_name.lower()
        )
        if open_request.status == AIToolRequestStatus.REQUESTED and same_tool:
            raise ConflictError(
                "You have already asked for this tool; it is waiting for a decision."
            )
    request = ai_tool_repository.create_request(
        db,
        AIToolRequest(
            requester_id=requester_id,
            tool_id=data.tool_id,
            tool_name=tool_name,
            domain=domain,
            purpose=data.purpose.strip(),
            data_involved=(data.data_involved or "").strip() or None,
            requested_on=_today(today),
            status=AIToolRequestStatus.REQUESTED,
        ),
    )
    audit_service.log(
        db, REQUEST_ENTITY_TYPE, request.id, "created", requester_id, {"tool_name": tool_name}
    )
    return request


def decide_request(
    db: Session,
    request_id: int,
    data: AIToolRequestDecision,
    actor_id: int | None,
    today: date | None = None,
) -> AIToolRequest:
    """The Chief AI Governance Officer answers a request. Approving it
    approves the tool (creating it if it was not yet catalogued); rejecting
    it needs a reason the employee can read. Nobody decides their own
    request."""
    governance_role_service.require_caigo(db, actor_id)
    request = _get_request_or_raise(db, request_id)
    if request.status != AIToolRequestStatus.REQUESTED:
        raise InvalidStatusTransitionError(f"This request is already {request.status}.")
    if actor_id is not None and actor_id == request.requester_id:
        raise ConflictError("You can't decide your own request.")
    reference = _today(today)
    note = (data.note or "").strip() or None

    if data.action == "reject":
        if note is None:
            raise ValidationError("Tell the employee why the tool isn't being approved.")
        request.status = AIToolRequestStatus.REJECTED
    else:
        tool = _tool_for_approval(db, request, data, actor_id)
        if tool.status in ALLOWED_STATUSES:
            raise InvalidStatusTransitionError(f"{tool.name} is already {tool.status}.")
        decide_tool(
            db,
            tool.id,
            AIToolDecision(
                action="approve",
                max_data_classification=data.max_data_classification,
                conditions_of_use=data.conditions_of_use,
                review_due=data.review_due,
                note=note,
            ),
            actor_id,
            today=reference,
        )
        request.tool_id = tool.id
        request.status = AIToolRequestStatus.APPROVED
    request.decided_by = actor_id
    request.decided_on = reference
    request.decision_note = note
    request = ai_tool_repository.save_request(db, request)
    audit_service.log(
        db,
        REQUEST_ENTITY_TYPE,
        request.id,
        f"decision_{data.action}",
        actor_id,
        {"status": request.status, "tool_id": request.tool_id, "note": note},
    )
    return request


def _tool_for_approval(
    db: Session, request: AIToolRequest, data: AIToolRequestDecision, actor_id: int | None
) -> AITool:
    """The tool an approved request is about: the one it named, one already
    catalogued at its address, or a new one."""
    if request.tool_id is not None:
        return _get_or_raise(db, request.tool_id)
    domain = ai_tool_domains.normalize_domain(data.domain) if data.domain else request.domain
    if domain is None:
        raise ValidationError("Add the tool's domain, so the browser knows which site to allow.")
    known = tool_for_host(db, domain)
    if known is not None:
        return known
    return create_tool(db, AIToolCreate(name=request.tool_name, domains=[domain]), actor_id)


# ---------- for the dashboard and compliance ----------


def pending_request_count(db: Session) -> int:
    return len(ai_tool_repository.list_open_requests(db))


def review_overdue_count(db: Session, today: date | None = None) -> int:
    return sum(1 for tool in ai_tool_repository.list_all(db) if review_overdue(tool, today))


def requestable_tools(db: Session) -> list[AITool]:
    """Known tools an employee could ask for: catalogued, or approved once
    and since revoked."""
    return [tool for tool in ai_tool_repository.list_all(db) if tool.status not in ALLOWED_STATUSES]


def approved_tools(db: Session) -> list[AITool]:
    return [tool for tool in ai_tool_repository.list_all(db) if tool.status in ALLOWED_STATUSES]
