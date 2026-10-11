"""AI systems tagged to framework controls, and how the compliance view
judges them."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories import framework_control_repository, sheet_repository
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    compliance_status_service,
    framework_service,
)

RESOURCE_COLUMNS = {
    "resource_documentation": "Architecture overview in the wiki",
    "data_resources": "Applicant records, 2020-2025",
    "tooling_frameworks": "PyTorch, MLflow",
    "tooling_documentation": "Tooling register v3",
    "compute_infrastructure": "Two A100 nodes",
    "hosting_environment": "EU-region private cloud",
    "development_team": "ML platform team",
    "oversight_roles": "AI System Owner, Risk Owner",
}


def control_id(db: Session, code: str) -> int:
    return next(
        c.id for c in framework_control_repository.list_all(db, "iso_42001") if c.code == code
    )


def make_system(db: Session, **data) -> int:
    row = {"name": "Resume Screener", "lifecycle_stage": "deployed", **data}
    return ai_system_inventory_service.add_row(db, row, actor_id=None).id


def tag(db: Session, row_id: int, code: str) -> int:
    cid = control_id(db, code)
    framework_service.set_tags(db, "AISystem", row_id, [cid], actor_id=None)
    return cid


def status_for(db: Session, cid: int):
    return next(r for r in compliance_status_service.get_status(db) if r.id == cid)


def test_a_system_with_its_resources_recorded_covers_the_resource_control(
    db_session: Session,
) -> None:
    row_id = make_system(db_session, **RESOURCE_COLUMNS)
    cid = tag(db_session, row_id, "A.4.5")

    row = status_for(db_session, cid)

    assert row.status == "satisfied"
    assert row.tagged_items[0].label == "Resume Screener"
    assert row.tagged_items[0].detail == "Resource information recorded"


def test_each_resource_control_looks_at_its_own_columns(db_session: Session) -> None:
    # Only the data resources are recorded, so only A.4.3 is covered.
    row_id = make_system(db_session, data_resources="Applicant records")
    covered = tag(db_session, row_id, "A.4.3")
    framework_service.set_tags(
        db_session,
        "AISystem",
        row_id,
        [covered, control_id(db_session, "A.4.2"), control_id(db_session, "A.4.5")],
        actor_id=None,
    )

    by_code = {
        r.code: r
        for r in compliance_status_service.get_status(db_session)
        if r.code in ("A.4.2", "A.4.3", "A.4.5")
    }

    assert by_code["A.4.3"].status == "satisfied"
    assert by_code["A.4.2"].status == "partial"
    assert by_code["A.4.2"].tagged_items[0].detail == "Not recorded yet: Resource Documentation"
    # Both columns are named when both are missing.
    assert by_code["A.4.5"].tagged_items[0].detail == (
        "Not recorded yet: Compute Infrastructure, Hosting Environment"
    )


def test_a_control_needing_two_columns_isnt_covered_by_one(db_session: Session) -> None:
    row_id = make_system(db_session, tooling_frameworks="PyTorch")
    cid = tag(db_session, row_id, "A.4.4")

    row = status_for(db_session, cid)

    assert row.status == "partial"
    assert row.tagged_items[0].detail == "Not recorded yet: Tooling Documentation"


def test_whitespace_alone_is_not_a_recorded_resource(db_session: Session) -> None:
    row_id = make_system(db_session, resource_documentation="   ")
    cid = tag(db_session, row_id, "A.4.2")

    assert status_for(db_session, cid).status == "partial"


def test_a_system_tagged_to_any_other_control_counts_while_it_is_in_service(
    db_session: Session,
) -> None:
    row_id = make_system(db_session)
    cid = tag(db_session, row_id, "A.6.2.5")

    row = status_for(db_session, cid)

    assert row.status == "satisfied"
    # The stage comes from the lifecycle: a new system starts at inception.
    assert row.tagged_items[0].detail == "AI system in inception"


def test_an_archived_system_stops_counting(db_session: Session) -> None:
    row_id = make_system(db_session, **RESOURCE_COLUMNS)
    cid = tag(db_session, row_id, "A.4.2")
    lifecycle = ai_system_lifecycle_service.get_or_create(db_session, row_id)
    lifecycle.archived_at = datetime.now(UTC)
    db_session.commit()

    row = status_for(db_session, cid)

    assert row.status == "partial"
    assert row.tagged_items[0].detail == "AI system has been archived"


def test_a_tag_pointing_at_a_deleted_system_is_not_coverage(db_session: Session) -> None:
    row_id = make_system(db_session, **RESOURCE_COLUMNS)
    cid = tag(db_session, row_id, "A.4.2")
    # Remove the row behind the tag's back, as if the tag had been orphaned.
    sheet_repository.delete_row(db_session, sheet_repository.get_row(db_session, row_id))

    assert status_for(db_session, cid).status == "no_coverage"


def test_a_tag_on_a_row_of_another_sheet_is_not_an_ai_system(db_session: Session) -> None:
    from app.services import data_inventory_service

    dataset = data_inventory_service.add_row(
        db_session, {"dataset_name": "Applicants"}, actor_id=None
    )
    cid = control_id(db_session, "A.4.2")
    framework_service.set_tags(db_session, "AISystem", dataset.id, [cid], actor_id=None)

    assert status_for(db_session, cid).status == "no_coverage"


def test_the_tag_shows_the_systems_name_in_the_mapping_view(db_session: Session) -> None:
    row_id = make_system(db_session, name="Fraud Detection Model")
    cid = tag(db_session, row_id, "A.6.2.5")

    labels = [
        item.label
        for control in framework_service.get_mapping(db_session)
        if control.id == cid
        for item in control.tagged_items
    ]

    assert labels == ["Fraud Detection Model"]


def test_deleting_an_ai_system_removes_its_tags(db_session: Session) -> None:
    row_id = make_system(db_session)
    cid = tag(db_session, row_id, "A.6.2.5")

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    assert framework_service.get_tags(db_session, "AISystem", row_id) == []
    assert status_for(db_session, cid).status == "no_coverage"
