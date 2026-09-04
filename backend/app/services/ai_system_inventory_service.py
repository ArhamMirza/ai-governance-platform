from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.lifecycle_stages import LifecycleStage
from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef
from app.services import audit_service, sheet_service

ENTITY_TYPE = "AISystemInventory"

STAGE_COLUMN_KEY = "lifecycle_stage"

DEFAULT_COLUMNS = [
    # System Overview
    ColumnDef(key="name", label="Name"),
    ColumnDef(key="description", label="Description"),
    ColumnDef(key="purpose", label="Purpose"),
    ColumnDef(key="lifecycle_stage", label="Lifecycle Stage"),
    ColumnDef(key="risk_tier", label="Risk Tier"),
    # Resource documentation -- ISO 42001 A.4.2/A.4.3. Per-dataset detail
    # (A.7) lives in the separate Data Inventory, so data_resources here is
    # a documentation-level summary, not a full register.
    ColumnDef(key="resource_documentation", label="Resource Documentation"),
    ColumnDef(key="data_resources", label="Data Resources"),
    # Tooling -- A.4.4
    ColumnDef(key="tooling_frameworks", label="Tooling & Frameworks"),
    ColumnDef(key="tooling_documentation", label="Tooling Documentation"),
    # System & computing resources -- A.4.5
    ColumnDef(key="compute_infrastructure", label="Compute Infrastructure"),
    ColumnDef(key="hosting_environment", label="Hosting Environment"),
    # Human resources -- A.4.6
    ColumnDef(key="development_team", label="Development Team"),
    ColumnDef(key="oversight_roles", label="Oversight Roles"),
]

# New A.4 columns not present in an already-provisioned inventory sheet get
# appended to it by a one-off data migration -- a fresh install just gets
# them from DEFAULT_COLUMNS above on first use.
RESOURCE_COLUMN_KEYS = [c.key for c in DEFAULT_COLUMNS if c.key not in {
    "name", "description", "purpose", "lifecycle_stage", "risk_tier",
}]


def get_or_create_sheet(db: Session) -> Sheet:
    sheet = sheet_repository.get_by_entity_type(db, ENTITY_TYPE)
    if sheet is not None:
        return sheet
    return sheet_service.create_sheet(db, ENTITY_TYPE, "AI System Inventory", DEFAULT_COLUMNS)


def list_rows(db: Session) -> list[SheetRow]:
    sheet = get_or_create_sheet(db)
    return sheet_service.list_rows(db, sheet.id)


def set_columns(db: Session, columns: list[ColumnDef], actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.set_columns(db, sheet.id, columns)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "columns_updated", actor_id)
    return result


def add_row(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    from app.services import ai_system_lifecycle_service

    sheet = get_or_create_sheet(db)
    # Every system starts at Inception; the stage only moves through a gate.
    row = sheet_service.add_row(
        db, sheet.id, {**data, STAGE_COLUMN_KEY: LifecycleStage.INCEPTION}
    )
    ai_system_lifecycle_service.get_or_create(db, row.id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_added", actor_id, {"row_id": row.id})
    return row


def update_row(db: Session, row_id: int, data: dict, actor_id: int | None) -> SheetRow:
    sheet = get_or_create_sheet(db)
    # The stage cell is server-owned -- editing it in the grid would sidestep
    # every gate, so a supplied value is ignored rather than rejected.
    row = sheet_service.update_row(
        db, sheet.id, row_id, {k: v for k, v in data.items() if k != STAGE_COLUMN_KEY}
    )
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_updated", actor_id, {"row_id": row_id})
    return row


def delete_row(db: Session, row_id: int, actor_id: int | None) -> None:
    """Removing an AI system also removes the assessments performed on it --
    they describe a system that no longer exists, and their sheets, evidence
    and framework tags would otherwise be orphaned."""
    # Imported here rather than at module scope: both assessment services
    # import this one (to validate the AI system row), so a top-level import
    # would be circular.
    from app.services import (
        ai_system_lifecycle_service,
        impact_assessment_service,
        risk_assessment_service,
    )

    risk_assessment = risk_assessment_service.get_for_ai_system(db, row_id)
    if risk_assessment is not None:
        risk_assessment_service.delete_risk_assessment(db, risk_assessment.id, actor_id)

    impact_assessment = impact_assessment_service.get_for_ai_system(db, row_id)
    if impact_assessment is not None:
        impact_assessment_service.delete(db, impact_assessment.id, actor_id)

    ai_system_lifecycle_service.delete_for_ai_system(db, row_id)

    sheet = get_or_create_sheet(db)
    sheet_service.delete_row(db, sheet.id, row_id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_deleted", actor_id, {"row_id": row_id})


def export_xlsx(db: Session) -> bytes:
    sheet = get_or_create_sheet(db)
    return sheet_service.export_xlsx(db, sheet.id)


def import_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.import_upload(db, sheet.id, file)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "sheet_uploaded", actor_id)
    return result
