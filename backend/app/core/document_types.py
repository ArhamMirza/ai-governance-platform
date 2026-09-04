"""Document types a life cycle stage gate looks for.

Evidence is otherwise untyped -- a filename alone can't tell a gate whether
the design document it requires has actually been uploaded, so uploads made
against a gate carry one of these.
"""

from enum import StrEnum


class DocumentType(StrEnum):
    DESIGN_DOCUMENT = "design_document"
    VALIDATION_REPORT = "validation_report"
    MONITORING_PLAN = "monitoring_plan"
    RETIREMENT_SIGNOFF = "retirement_signoff"


DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.DESIGN_DOCUMENT: "Design document",
    DocumentType.VALIDATION_REPORT: "Validation report",
    DocumentType.MONITORING_PLAN: "Monitoring plan",
    DocumentType.RETIREMENT_SIGNOFF: "Retirement sign-off",
}
