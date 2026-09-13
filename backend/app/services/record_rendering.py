"""Turning a governance record into text a search can find.

A record is already structured, so this is not extraction in the sense that
reading a PDF is -- it is choosing what a passage about this record should
say, and saying it in a form that survives both retrievers.

Two rules shape every renderer here:

**Keep the values exact.** "Likelihood: 4" stays "4". Keyword search is
carried precisely so that a control id, a score or a date can be matched
literally, and paraphrasing a record into prose would throw that away.

**Label every value.** A retrieved passage has to be readable on its own: a
bare list of cells means nothing to the person reading the citation, and
means nothing to the model either.

What this deliberately does not do is replace reading the record. Retrieval
finds the right material across the estate; anything that needs a current,
exact value should read the row.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.chunking import Segment
from app.models.data_inventory_record import DataInventoryRecord
from app.models.document_chunk import SourceType
from app.models.impact_assessment import ImpactAssessment
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.models.sheet import Sheet, SheetRow

# The sheet each kind of row lives on, so a row can be found by its kind.
SHEET_ENTITY_FOR_SOURCE = {
    SourceType.AI_SYSTEM: "AISystemInventory",
    SourceType.DATA_INVENTORY: "DataInventory",
    SourceType.RISK_ITEM: "RiskAssessment",
}


@dataclass
class RenderedRecord:
    """One record as indexable text, plus how a citation should name it."""

    title: str
    segments: list[Segment]
    entity_type: str
    entity_id: int


def _lines(pairs: list[tuple[str, object]]) -> str:
    """Labelled values, one per line, skipping the ones nobody filled in."""
    return "\n".join(f"{label}: {value}" for label, value in pairs if str(value or "").strip())


def _titled(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


# ---------- policies and procedures ----------


def _render_policy(db: Session, policy_id: int) -> RenderedRecord | None:
    policy = db.get(Policy, policy_id)
    if policy is None:
        return None
    body = _lines(
        [
            ("Title", policy.title),
            ("Description", policy.description),
            ("Status", policy.status),
            ("Version", policy.version),
            ("Effective date", policy.effective_date),
            ("Next review date", policy.next_review_date),
        ]
    )
    return RenderedRecord(
        title=f"Policy: {policy.title}",
        segments=[Segment(text=body, section="Policy record")],
        entity_type=SourceType.POLICY,
        entity_id=policy.id,
    )


def _render_procedure(db: Session, procedure_id: int) -> RenderedRecord | None:
    procedure = db.get(Procedure, procedure_id)
    if procedure is None:
        return None
    body = _lines(
        [
            ("Title", procedure.title),
            ("Description", procedure.description),
            ("Status", procedure.status),
            ("Version", procedure.version),
            ("Effective date", procedure.effective_date),
            ("Next review date", procedure.next_review_date),
        ]
    )
    return RenderedRecord(
        title=f"Procedure: {procedure.title}",
        segments=[Segment(text=body, section="Procedure record")],
        entity_type=SourceType.PROCEDURE,
        entity_id=procedure.id,
    )


# ---------- sheet rows: AI systems, data inventory, risk items ----------


def _render_sheet_row(db: Session, source_type: str, row_id: int) -> RenderedRecord | None:
    row = db.get(SheetRow, row_id)
    if row is None:
        return None
    sheet = db.get(Sheet, row.sheet_id)
    if sheet is None or sheet.entity_type != SHEET_ENTITY_FOR_SOURCE.get(source_type):
        # The row exists but is not the kind this source type describes --
        # a stale queue entry after a sheet was replaced, for instance.
        return None

    data = dict(row.data or {})
    # The sheet's own column definitions carry the human labels; anything
    # the sheet doesn't define still gets indexed under its raw key rather
    # than being dropped.
    labels = {
        str(column.get("key")): str(column.get("label") or column.get("key"))
        for column in (sheet.columns or [])
        if column.get("key")
    }
    ordered = [(labels.get(key, key), value) for key, value in data.items()]

    name = _titled(
        data.get("name") or data.get("title") or data.get("description"),
        f"row {row.row_index + 1}",
    )
    kind = {
        SourceType.AI_SYSTEM: "AI system",
        SourceType.DATA_INVENTORY: "Data inventory",
        SourceType.RISK_ITEM: "Risk item",
    }[source_type]

    return RenderedRecord(
        title=f"{kind}: {name}",
        segments=[Segment(text=_lines(ordered), section=f"{kind} record")],
        entity_type=source_type,
        entity_id=row.id,
    )


# ---------- impact assessments ----------

_NARRATIVE_FIELDS = [
    ("System description", "system_description"),
    ("Intended purpose", "intended_purpose"),
    ("Foreseeable misuse", "foreseeable_misuse"),
    ("Data and model information", "data_and_model_info"),
    ("Deployment environment", "deployment_environment"),
    ("Affected interested parties", "affected_interested_parties"),
    ("Human oversight role", "human_oversight_role"),
    ("Conclusion", "conclusion"),
]


def _render_impact_assessment(db: Session, assessment_id: int) -> RenderedRecord | None:
    assessment = db.get(ImpactAssessment, assessment_id)
    if assessment is None:
        return None

    system_name = ""
    row = db.get(SheetRow, assessment.ai_system_row_id)
    if row is not None:
        system_name = _titled(dict(row.data or {}).get("name"), "")

    # One segment per section, so a citation names the section a claim came
    # from rather than "this assessment" -- and so an assessment with eight
    # long narratives is not one unretrievable blob.
    segments = [
        Segment(
            text=_lines(
                [
                    ("Status", assessment.status),
                    ("AI system", system_name),
                    ("Assessment date", assessment.assessment_date),
                    ("Next review date", assessment.next_review_date),
                ]
            ),
            section="Impact assessment summary",
        )
    ]
    for label, attribute in _NARRATIVE_FIELDS:
        text = str(getattr(assessment, attribute, "") or "").strip()
        if text:
            segments.append(Segment(text=f"{label}: {text}", section=label))

    from app.models.impact_factor_assessment import ImpactFactorAssessment

    factors = (
        db.query(ImpactFactorAssessment)
        .filter(ImpactFactorAssessment.impact_assessment_id == assessment_id)
        .order_by(ImpactFactorAssessment.id)
        .all()
    )
    for scored in factors:
        body = _lines(
            [
                ("Factor", scored.factor),
                ("Score", scored.score),
                ("Benefits", scored.benefits),
                ("Harms", scored.harms),
                ("Scoring criteria", scored.criteria),
            ]
        )
        if body:
            segments.append(Segment(text=body, section=f"Impact factor: {scored.factor}"))

    label = f"Impact assessment: {system_name}" if system_name else "Impact assessment"
    return RenderedRecord(
        title=label,
        segments=segments,
        entity_type=SourceType.IMPACT_ASSESSMENT,
        entity_id=assessment.id,
    )


# ---------- data inventory approval records ----------


def _render_data_inventory_record(db: Session, record_id: int) -> RenderedRecord | None:
    """The approval state of a data inventory row, indexed with its row."""
    record = db.get(DataInventoryRecord, record_id)
    if record is None:
        return None
    return _render_sheet_row(db, SourceType.DATA_INVENTORY, record.data_inventory_row_id)


RENDERERS = {
    SourceType.POLICY: _render_policy,
    SourceType.PROCEDURE: _render_procedure,
    SourceType.IMPACT_ASSESSMENT: _render_impact_assessment,
    SourceType.AI_SYSTEM: lambda db, i: _render_sheet_row(db, SourceType.AI_SYSTEM, i),
    SourceType.DATA_INVENTORY: lambda db, i: _render_sheet_row(db, SourceType.DATA_INVENTORY, i),
    SourceType.RISK_ITEM: lambda db, i: _render_sheet_row(db, SourceType.RISK_ITEM, i),
}


def render(db: Session, source_type: str, source_id: int) -> RenderedRecord | None:
    """One record as indexable text, or None if it is gone or not indexable."""
    renderer = RENDERERS.get(source_type)
    if renderer is None:
        return None
    rendered = renderer(db, source_id)
    if rendered is None or not any(s.text.strip() for s in rendered.segments):
        return None
    return rendered
