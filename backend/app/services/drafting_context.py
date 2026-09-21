"""Shared context-gathering helpers for the drafting services.

Distinct from pinned_context.py: that module's contract is "always
included, unconditionally, in every prompt that asks for it." These are
gathered, ranked candidate sources for one specific drafting call --
capped and deduplicated like anything else a `_gather()` collects, not
unconditionally pinned.

Extracted from organization_context_drafting_service.py once a second and
third drafting service needed the same summaries, rather than copying
them again.
"""

from sqlalchemy.orm import Session

from app.models.policy import PolicyStatus
from app.models.procedure import ProcedureStatus
from app.services import ai_system_inventory_service, policy_service, procedure_service

MAX_SUMMARY_ROWS = 20


def _capped(lines: list[str]) -> str:
    shown = lines[:MAX_SUMMARY_ROWS]
    if len(lines) > MAX_SUMMARY_ROWS:
        shown.append(f"...and {len(lines) - MAX_SUMMARY_ROWS} more not shown.")
    return "\n".join(shown)


def ai_systems_summary(db: Session) -> dict | None:
    rows = ai_system_inventory_service.list_rows(db)
    lines = [
        f"- {data.get('name') or 'Unnamed system'}: {data.get('purpose')}"
        if (data := row.data or {}).get("purpose")
        else f"- {data.get('name') or 'Unnamed system'}"
        for row in rows
    ]
    if not lines:
        return None
    return {
        "n": 0,
        "title": "AI systems in the inventory",
        "section": None,
        "kind": "AISystemsSummary",
        "text": _capped(lines),
        "href": "/ai-systems",
        "download_evidence_id": None,
        "read_by_ocr": False,
        "injection_findings": [],
    }


def policies_summary(db: Session, *, exclude_id: int | None = None) -> dict | None:
    lines = [
        f"- {p.title}: {p.description}"
        for p in policy_service.list_policies(db)
        if p.id != exclude_id
        and p.status != PolicyStatus.RETIRED
        and (p.description or "").strip()
    ]
    if not lines:
        return None
    return {
        "n": 0,
        "title": "Policies",
        "section": None,
        "kind": "PoliciesSummary",
        "text": _capped(lines),
        "href": "/policies",
        "download_evidence_id": None,
        "read_by_ocr": False,
        "injection_findings": [],
    }


def procedures_summary(db: Session, *, exclude_id: int | None = None) -> dict | None:
    lines = [
        f"- {p.title}: {p.description}"
        for p in procedure_service.list_procedures(db)
        if p.id != exclude_id
        and p.status != ProcedureStatus.RETIRED
        and (p.description or "").strip()
    ]
    if not lines:
        return None
    return {
        "n": 0,
        "title": "Procedures",
        "section": None,
        "kind": "ProceduresSummary",
        "text": _capped(lines),
        "href": "/procedures",
        "download_evidence_id": None,
        "read_by_ocr": False,
        "injection_findings": [],
    }
