"""Read-only functions the chat assistant may call for an exact answer.

Retrieval answers "what does the record say about X" well. It answers
"how many AI systems have no impact assessment" badly: that is a count over
every row, and a fused, floor-gated top-k search is the wrong tool for a
question whose answer is a number, not a passage. These functions compute
that number the same way the dashboard does, so the assistant's answer and
the dashboard's count can never disagree.

Every function here is read-only by construction -- there is no tool that
writes anything, named here or anywhere the model can reach. That is the
architectural control the whole AI design rests on: a model that decides to
call every tool in this file, with the most adversarial arguments it can
invent, still cannot change a single record. At worst it returns a
governance summary to someone who could have read the dashboard themselves.

Each tool is capped in what it returns -- a row limit, a character limit per
field -- so one call cannot swallow the model's whole context on an org with
thousands of rows. What a limit hides, the tool says so explicitly, so the
assistant can tell the person rather than presenting a partial count as
complete.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.core.exceptions import ValidationError
from app.core.risk_scoring import SEVERITY_HIGH, SEVERITY_LOW, SEVERITY_MEDIUM
from app.models.sheet import SheetRow
from app.repositories import sheet_repository
from app.services import (
    ai_system_inventory_service,
    dashboard_service,
    impact_assessment_service,
    risk_analytics_service,
    risk_assessment_service,
    risk_criteria_service,
)

MAX_ROWS = 30
MAX_FIELD_CHARS = 300
_SEVERITIES = {SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW}


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        return value[:MAX_FIELD_CHARS] + "…"
    return value


def _capped(rows: list[dict], limit: int) -> dict:
    """A row list, bounded, with the truncation stated rather than hidden."""
    bounded = min(max(limit, 1), MAX_ROWS)
    return {
        "count": len(rows),
        "rows": rows[:bounded],
        "truncated": len(rows) > bounded,
    }


# ---------- coverage_summary ----------


def _coverage_summary(db: Session, actor_id: int | None, _args: dict) -> dict:
    summary = dashboard_service.get_summary(db, actor_id)
    return {
        "ai_systems_total": summary.coverage.ai_systems_total,
        "ai_systems_impact_assessed": summary.coverage.ai_systems_impact_assessed,
        "ai_systems_risk_assessed": summary.coverage.ai_systems_assessed,
        "assessments_review_overdue": summary.coverage.assessments_review_overdue,
        "policies_total": summary.coverage.policies_total,
        "policies_approved": summary.coverage.policies_approved,
        "procedures_total": summary.coverage.procedures_total,
        "procedures_approved": summary.coverage.procedures_approved,
        "attention_items": [
            {"label": item.label, "count": item.count}
            for item in summary.attention
            if item.count > 0
        ],
    }


# ---------- list_ai_systems ----------


def _ai_system_row(db: Session, row: SheetRow) -> dict:
    data = row.data or {}
    return {
        "id": row.id,
        "name": _clip(data.get("name")) or f"row {row.row_index + 1}",
        "risk_tier": data.get("risk_tier"),
        "lifecycle_stage": data.get("lifecycle_stage"),
        "has_completed_impact_assessment": impact_assessment_service.has_completed_for_ai_system(
            db, row.id
        ),
        "has_risk_assessment": risk_assessment_service.get_for_ai_system(db, row.id) is not None,
    }


def _list_ai_systems(db: Session, _actor_id: int | None, args: dict) -> dict:
    risk_tier = args.get("risk_tier")
    missing_impact_assessment = args.get("missing_impact_assessment")
    missing_risk_assessment = args.get("missing_risk_assessment")

    rows = []
    for row in ai_system_inventory_service.list_rows(db):
        entry = _ai_system_row(db, row)
        if risk_tier and str(entry["risk_tier"] or "").lower() != str(risk_tier).lower():
            continue
        if missing_impact_assessment is True and entry["has_completed_impact_assessment"]:
            continue
        if missing_impact_assessment is False and not entry["has_completed_impact_assessment"]:
            continue
        if missing_risk_assessment is True and entry["has_risk_assessment"]:
            continue
        if missing_risk_assessment is False and not entry["has_risk_assessment"]:
            continue
        rows.append(entry)
    return _capped(rows, args.get("limit", MAX_ROWS))


# ---------- list_risk_items ----------


def _list_risk_items(db: Session, _actor_id: int | None, args: dict) -> dict:
    severity = args.get("severity")
    if severity is not None and severity not in _SEVERITIES:
        raise ValidationError(f"severity must be one of {sorted(_SEVERITIES)}")
    overdue_only = bool(args.get("overdue_only"))
    bands = risk_criteria_service.get_bands(db)

    rows = []
    for assessment in risk_assessment_service.list_risk_assessments(db):
        system_row = sheet_repository.get_row(db, assessment.ai_system_row_id)
        system_name = (system_row.data or {}).get("name") if system_row else None
        for item in risk_assessment_service.list_rows(db, assessment.id):
            score = risk_analytics_service.inherent_score(item)
            item_severity = (
                risk_scoring.severity_for_score(score, bands) if score is not None else None
            )
            data = item.data or {}
            if severity and item_severity != severity:
                continue
            if overdue_only and not risk_scoring.is_overdue(data):
                continue
            rows.append(
                {
                    "ai_system": system_name,
                    "category": _clip(data.get("category")),
                    "description": _clip(data.get("description")),
                    "severity": item_severity,
                    "inherent_score": score,
                    "residual_score": risk_analytics_service.residual_score(item),
                    "status": data.get("status"),
                    "risk_owner": data.get("risk_owner"),
                    "treatment_deadline": data.get("treatment_deadline"),
                }
            )
    # Highest severity and soonest deadline first, so a capped list still
    # surfaces the rows most likely to be what was asked about.
    order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_LOW: 2, None: 3}
    rows.sort(key=lambda r: (order.get(r["severity"], 3), r["treatment_deadline"] or ""))
    return _capped(rows, args.get("limit", MAX_ROWS))


# ---------- get_ai_system_record ----------


def _get_ai_system_record(db: Session, _actor_id: int | None, args: dict) -> dict:
    needle = str(args.get("name_or_id", "")).strip()
    if not needle:
        raise ValidationError("name_or_id is required")

    row = None
    if needle.isdigit():
        row = sheet_repository.get_row(db, int(needle))
    if row is None:
        needle_lower = needle.lower()
        for candidate in ai_system_inventory_service.list_rows(db):
            if str((candidate.data or {}).get("name", "")).strip().lower() == needle_lower:
                row = candidate
                break
    if row is None:
        return {"found": False, "searched_for": needle}

    data = {k: _clip(v) for k, v in (row.data or {}).items()}
    assessment = impact_assessment_service.get_for_ai_system(db, row.id)
    risk = risk_assessment_service.get_for_ai_system(db, row.id)
    return {
        "found": True,
        "id": row.id,
        "fields": data,
        "impact_assessment_status": str(assessment.status) if assessment else None,
        "risk_assessment_status": str(risk.status) if risk else None,
    }


# ---------- registry ----------

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "governance_coverage_summary",
            "description": (
                "Exact, organisation-wide governance coverage: how many AI systems, "
                "policies and procedures exist, how many are assessed or approved, and "
                "what currently needs attention. Use for any question about totals, "
                "counts or 'what's missing' across the whole organisation -- never guess "
                "these numbers from retrieved text."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_ai_systems",
            "description": (
                "List AI systems in the inventory, optionally filtered by risk tier or by "
                "whether they have a completed impact assessment or a risk assessment. Use "
                "for questions like 'which systems have no impact assessment' or 'list our "
                "high risk tier systems'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_tier": {"type": "string", "description": "e.g. 'high', 'medium', 'low'"},
                    "missing_impact_assessment": {
                        "type": "boolean",
                        "description": "true = only systems with no completed impact assessment",
                    },
                    "missing_risk_assessment": {
                        "type": "boolean",
                        "description": "true = only systems with no risk assessment",
                    },
                    "limit": {"type": "integer", "description": f"max rows, up to {MAX_ROWS}"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_risk_items",
            "description": (
                "List individual risk items across every risk assessment, optionally "
                "filtered by severity (computed from likelihood x impact against this "
                "organisation's own risk criteria) or restricted to overdue treatments. Use "
                "for 'list the high risks' or 'what risk treatments are overdue'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": sorted(_SEVERITIES)},
                    "overdue_only": {"type": "boolean"},
                    "limit": {"type": "integer", "description": f"max rows, up to {MAX_ROWS}"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ai_system_record",
            "description": (
                "The exact current field values of one AI system inventory row, by name or "
                "id -- and its impact/risk assessment status. Use this instead of retrieved "
                "text whenever the answer needs a precise, current value: a score, a status, "
                "a field the record just changed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_id": {"type": "string"},
                },
                "required": ["name_or_id"],
            },
        },
    },
]

# Human-readable label and page link for each tool, used to present its
# result as a source: what an assistant answer built on it should be called,
# and where a reader can go to see the same thing themselves.
TOOL_PRESENTATION: dict[str, tuple[str, str]] = {
    "governance_coverage_summary": ("Live lookup: governance coverage summary", "/"),
    "list_ai_systems": ("Live lookup: AI system inventory", "/ai-systems"),
    "list_risk_items": ("Live lookup: risk items", "/risk-assessments"),
    "get_ai_system_record": ("Live lookup: AI system record", "/ai-systems"),
}

_DISPATCH = {
    "governance_coverage_summary": _coverage_summary,
    "list_ai_systems": _list_ai_systems,
    "list_risk_items": _list_risk_items,
    "get_ai_system_record": _get_ai_system_record,
}


def run_tool(db: Session, actor_id: int | None, name: str, arguments: dict) -> dict:
    """Execute one tool call. Never raises for a model's own bad arguments --
    those come back as a result the model can read and correct from,
    the same as a person mistyping a filter."""
    handler = _DISPATCH.get(name)
    if handler is None:
        return {"error": f"No such tool: {name}"}
    try:
        return handler(db, actor_id, arguments or {})
    except ValidationError as exc:
        return {"error": str(exc)}
