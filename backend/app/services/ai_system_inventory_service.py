from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.lifecycle_stages import LifecycleStage
from app.models.sheet import Sheet, SheetRow
from app.schemas.sheet import ColumnDef
from app.services import audit_service, evidence_service, sheet_service

ENTITY_TYPE = "AISystemInventory"

# What the AI system's own documents (stage-gate uploads, and anything filed
# through its document browser) are tagged with -- a different string from
# this module's own ENTITY_TYPE above, which names the inventory *sheet*.
# See ai_system_lifecycle_service.AI_SYSTEM_ENTITY_TYPE, the same value.
AI_SYSTEM_DOCUMENT_ENTITY_TYPE = "AISystem"

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
    # Operation -- A.6.2.8 (and EU AI Act Art. 12 / Art. 19)
    ColumnDef(key="event_logging", label="Event Logging"),
    ColumnDef(key="log_retention", label="Log Retention"),
    # Information for users and customers -- A.8.2 / A.10.4
    ColumnDef(key="user_information", label="Information for Users"),
    ColumnDef(key="customer_information", label="Information for Customers"),
]

# Which inventory columns document each control, so an AI system tagged to
# one of them only counts as covering it once those are filled in (see
# compliance_status_service._resolve_ai_system).
CONTROL_COLUMNS: dict[str, list[str]] = {
    "A.4.2": ["resource_documentation"],
    "A.4.3": ["data_resources"],
    "A.4.4": ["tooling_frameworks", "tooling_documentation"],
    "A.4.5": ["compute_infrastructure", "hosting_environment"],
    "A.4.6": ["development_team", "oversight_roles"],
    "A.6.2.8": ["event_logging", "log_retention"],
    "A.8.2": ["user_information"],
    "A.10.4": ["customer_information"],
    "Art.12": ["event_logging"],
    "Art.19": ["log_retention"],
}

# The A.4 columns that migration 84cc2880ae2a appended to an
# already-provisioned inventory sheet. Listed explicitly, not derived from
# DEFAULT_COLUMNS, so columns added later don't silently join that migration.
RESOURCE_COLUMN_KEYS = [
    "resource_documentation",
    "data_resources",
    "tooling_frameworks",
    "tooling_documentation",
    "compute_infrastructure",
    "hosting_environment",
    "development_team",
    "oversight_roles",
]


def get_or_create_sheet(db: Session) -> Sheet:
    return sheet_service.get_or_create_singleton_sheet(
        db, ENTITY_TYPE, "AI System Inventory", DEFAULT_COLUMNS
    )


def _archived_row_ids(db: Session) -> set[int]:
    from app.repositories import ai_system_lifecycle_repository

    return {
        lifecycle.ai_system_row_id
        for lifecycle in ai_system_lifecycle_repository.list_all(db)
        if lifecycle.archived_at is not None
    }


def list_rows(db: Session, include_archived: bool = False) -> list[SheetRow]:
    """Archived systems are retired records, not part of the active estate --
    they're excluded from the inventory grid and from coverage counts, and
    listed on their own in the archive."""
    sheet = get_or_create_sheet(db)
    rows = sheet_service.list_rows(db, sheet.id)
    if include_archived:
        return rows
    archived = _archived_row_ids(db)
    return [row for row in rows if row.id not in archived]


def list_archived_rows(db: Session) -> list[SheetRow]:
    sheet = get_or_create_sheet(db)
    archived = _archived_row_ids(db)
    return [row for row in sheet_service.list_rows(db, sheet.id) if row.id in archived]


def set_columns(db: Session, columns: list[ColumnDef], actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.set_columns(db, sheet.id, columns)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "columns_updated", actor_id)
    return result


def add_row(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    from app.services import ai_system_lifecycle_service

    sheet = get_or_create_sheet(db)
    # Every system starts at Inception; the stage only moves through a gate.
    row = sheet_service.add_row(db, sheet.id, {**data, STAGE_COLUMN_KEY: LifecycleStage.INCEPTION})
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
    and framework tags would otherwise be orphaned.

    Datasets are unlinked rather than deleted: a Data Inventory entry is an
    organizational data asset with its own owner and review, so it outlives
    any one system that used it (see data_inventory_service.unlink_ai_system).
    Incidents are unlinked for the same reason: they record what happened,
    which stays true after the system is gone. So are suppliers: the
    relationship outlives any one system it contributed to."""
    # Imported here rather than at module scope: both assessment services
    # import this one (to validate the AI system row), so a top-level import
    # would be circular.
    from app.services import (
        ai_incident_service,
        ai_system_lifecycle_service,
        change_service,
        concern_service,
        data_inventory_service,
        framework_service,
        impact_assessment_service,
        objective_service,
        risk_assessment_service,
        supplier_service,
    )

    # Retention is the whole point of the archive: an archived record can't be
    # deleted until the period the organization set has actually run out.
    lifecycle = ai_system_lifecycle_service.get_or_create(db, row_id)
    if lifecycle.archived_at is not None and not ai_system_lifecycle_service.retention_expired(
        lifecycle
    ):
        raise ConflictError(
            "This archived system is kept until "
            f"{lifecycle.retention_until}. It can't be deleted before then."
        )

    risk_assessment = risk_assessment_service.get_for_ai_system(db, row_id)
    if risk_assessment is not None:
        risk_assessment_service.delete_risk_assessment(db, risk_assessment.id, actor_id)

    impact_assessment = impact_assessment_service.get_for_ai_system(db, row_id)
    if impact_assessment is not None:
        impact_assessment_service.delete(db, impact_assessment.id, actor_id)

    data_inventory_service.unlink_ai_system(db, row_id, actor_id)
    ai_incident_service.unlink_ai_system(db, row_id, actor_id)
    supplier_service.unlink_ai_system(db, row_id, actor_id)
    objective_service.unlink_ai_system(db, row_id, actor_id)
    change_service.unlink_ai_system(db, row_id, actor_id)
    concern_service.unlink_ai_system(db, row_id, actor_id)
    ai_system_lifecycle_service.delete_for_ai_system(db, row_id)
    evidence_service.delete_all_for_entity(db, AI_SYSTEM_DOCUMENT_ENTITY_TYPE, row_id)
    framework_service.delete_tags(db, AI_SYSTEM_DOCUMENT_ENTITY_TYPE, row_id)

    sheet = get_or_create_sheet(db)
    sheet_service.delete_row(db, sheet.id, row_id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_deleted", actor_id, {"row_id": row_id})


def export_xlsx(db: Session) -> bytes:
    sheet = get_or_create_sheet(db)
    return sheet_service.export_xlsx(db, sheet.id)


def import_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    # Matched by name when the file has no ID column of its own -- see
    # sheet_service.import_upload. A matched row keeps its id, so its
    # lifecycle stays correctly attached instead of silently landing on
    # whatever row reuses that id next.
    outcome = sheet_service.import_upload(db, sheet.id, file, natural_key_column="name")
    audit_service.log(db, ENTITY_TYPE, sheet.id, "sheet_uploaded", actor_id)
    return outcome.sheet
