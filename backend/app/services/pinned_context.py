"""Organization-wide context threaded into every grounded AI call, not only
the ones retrieval happens to rank it for.

Two things live here: the governance roles (previously duplicated,
near-identically, in both drafting services) and the ISO/IEC 42001 Clause 4
context of the organization (its description, its overall use of AI, its
internal/external issues and its interested parties). Both are read
directly rather than retrieved and ranked -- an organization has one set of
governance roles and one context statement, and a person asking or drafting
anything should always have them in view, the same way a footnote isn't
found by search.

Deliberately never indexed for ranked search: the same content reaching a
prompt twice, once pinned here and once again as an independently-ranked
chunk, would spend tokens on near-duplicate text for nothing.

Capped regardless of size, so a growing table can't grow a prompt without
bound -- at most MAX_ROWS rows per table, each cell truncated to
MAX_CELL_CHARS, with a trailing note if the cap was hit.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance_role import GovernanceRole
from app.models.sheet import SheetRow

MAX_ROWS = 20
MAX_CELL_CHARS = 400


def governance_roles(db: Session) -> dict | None:
    """Every defined role and what it's responsible for, as one pinned
    source."""
    roles = list(db.scalars(select(GovernanceRole).order_by(GovernanceRole.id)))
    lines = [
        f"{role.name}: {role.responsibilities}"
        for role in roles
        if (role.responsibilities or "").strip()
    ]
    if not lines:
        return None
    return {
        "key": ("roles", 0),
        "title": "Governance roles and responsibilities",
        "section": None,
        "kind": "GovernanceRoles",
        "text": "\n".join(lines),
        "href": "/governance",
        "download_evidence_id": None,
        "read_by_ocr": False,
        "injection_findings": [],
    }


def _rendered_rows(rows: list[SheetRow], columns: list[str]) -> str:
    lines = []
    for row in rows[:MAX_ROWS]:
        parts = [
            f"{column}: {str(row.data.get(column) or '').strip()[:MAX_CELL_CHARS]}"
            for column in columns
            if str(row.data.get(column) or "").strip()
        ]
        if parts:
            lines.append("- " + "; ".join(parts))
    if len(rows) > MAX_ROWS:
        lines.append(f"...and {len(rows) - MAX_ROWS} more not shown.")
    return "\n".join(lines)


def organization_context(db: Session) -> dict | None:
    """The organization's ISO/IEC 42001 Clause 4 context, as one pinned
    source: its description, its overall use of AI, the scope of the AI
    management system, its internal/external issues and its interested parties."""
    from app.services import organization_context_service

    context = organization_context_service.get_or_create(db)
    parts = []
    if (context.organization_description or "").strip():
        parts.append(f"Organization description: {context.organization_description.strip()}")
    if (context.ai_usage_overview or "").strip():
        parts.append(f"Overall use of AI: {context.ai_usage_overview.strip()}")
    if (context.aims_scope or "").strip():
        parts.append(f"Scope of the AI management system: {context.aims_scope.strip()}")
    if (context.aims_scope_exclusions or "").strip():
        parts.append(f"Excluded from the scope: {context.aims_scope_exclusions.strip()}")

    issues = organization_context_service.list_issues(db)
    rendered_issues = _rendered_rows(issues, ["category", "issue", "planned_response"])
    if rendered_issues:
        parts.append(f"Internal and external issues:\n{rendered_issues}")

    parties = organization_context_service.list_interested_parties(db)
    rendered_parties = _rendered_rows(parties, ["party", "needs", "expectations", "requirements"])
    if rendered_parties:
        parts.append(f"Interested parties:\n{rendered_parties}")

    if not parts:
        return None
    return {
        "key": ("organization_context", 0),
        "title": "Context of the organization",
        "section": None,
        "kind": "OrganizationContext",
        "text": "\n\n".join(parts),
        "href": "/organization-context",
        "download_evidence_id": None,
        "read_by_ocr": False,
        "injection_findings": [],
    }
