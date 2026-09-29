"""Supplier and third-party register -- ISO/IEC 42001 Annex A.10.2-A.10.4.

Gated only by ordinary edit permission, like Incidents and Competence. When
a review is due and whether a contract needs attention are computed live
(app.core.supplier_schedule), never stored.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import supplier_schedule
from app.core.exceptions import NotFoundError, ValidationError
from app.core.supplier_schedule import ContractStatus
from app.models.supplier import Supplier, SupplierStatus
from app.models.supplier_review import SupplierReview
from app.repositories import sheet_repository, supplier_repository
from app.schemas.supplier import SupplierCreate, SupplierReviewCreate, SupplierUpdate
from app.services import ai_system_inventory_service, audit_service, framework_service

ENTITY_TYPE = "Supplier"
REVIEW_ENTITY_TYPE = "SupplierReview"


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


@dataclass(frozen=True)
class Standing:
    next_review_due: date | None
    review_overdue: bool
    contract_status: ContractStatus | None


def standing(supplier: Supplier, review_dates: list[date], today: date | None = None) -> Standing:
    reference = _today(today)
    is_active = supplier.status == SupplierStatus.ACTIVE
    next_due = supplier_schedule.next_review_due(
        supplier.review_interval_months, supplier.first_review_due, review_dates
    )
    return Standing(
        next_review_due=next_due,
        review_overdue=supplier_schedule.is_review_overdue(is_active, next_due, reference),
        contract_status=supplier_schedule.contract_status(
            is_active, supplier.contract_end, reference
        ),
    )


def review_dates_by_supplier(db: Session) -> dict[int, list[date]]:
    """Every supplier's review dates in one query, for list views and the
    dashboard rather than one query per supplier."""
    dates: dict[int, list[date]] = defaultdict(list)
    for review in supplier_repository.list_reviews(db):
        dates[review.supplier_id].append(review.review_date)
    return dates


def ai_systems_by_supplier(db: Session) -> dict[int, list[int]]:
    linked: dict[int, list[int]] = defaultdict(list)
    for link in supplier_repository.list_links(db):
        linked[link.supplier_id].append(link.ai_system_row_id)
    return linked


def _get_or_raise(db: Session, supplier_id: int) -> Supplier:
    supplier = supplier_repository.get(db, supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier", supplier_id)
    return supplier


def _validate(supplier: Supplier) -> None:
    """Checked against the supplier as it will be saved, so no partial
    update can leave it half-configured."""
    if (supplier.review_interval_months is None) != (supplier.first_review_due is None):
        raise ValidationError(
            "Set both how often the supplier is reviewed and when the first review "
            "is due, or neither."
        )
    if (
        supplier.contract_start is not None
        and supplier.contract_end is not None
        and supplier.contract_end < supplier.contract_start
    ):
        raise ValidationError("The contract can't end before it starts.")


def _validate_ai_system_rows(db: Session, row_ids: list[int]) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    for row_id in row_ids:
        row = sheet_repository.get_row(db, row_id)
        if row is None or row.sheet_id != inventory_sheet.id:
            raise NotFoundError("AISystemRow", row_id)


def list_suppliers(db: Session, ai_system_row_id: int | None = None) -> list[Supplier]:
    suppliers = supplier_repository.list_all(db)
    if ai_system_row_id is None:
        return suppliers
    linked = {
        link.supplier_id
        for link in supplier_repository.list_links_for_ai_system(db, ai_system_row_id)
    }
    return [supplier for supplier in suppliers if supplier.id in linked]


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    return _get_or_raise(db, supplier_id)


def list_reviews(db: Session, supplier_id: int) -> list[SupplierReview]:
    return supplier_repository.list_reviews_for_supplier(db, supplier_id)


def create_supplier(db: Session, data: SupplierCreate, actor_id: int | None) -> Supplier:
    supplier = Supplier(**data.model_dump(), status=SupplierStatus.ACTIVE)
    _validate(supplier)
    supplier = supplier_repository.create(db, supplier)
    audit_service.log(db, ENTITY_TYPE, supplier.id, "created", actor_id, {"name": supplier.name})
    return supplier


def update_supplier(
    db: Session, supplier_id: int, data: SupplierUpdate, actor_id: int | None
) -> Supplier:
    supplier = _get_or_raise(db, supplier_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(supplier, field, value)
    try:
        _validate(supplier)
    except ValidationError:
        db.rollback()
        raise
    supplier = supplier_repository.save(db, supplier)
    audit_service.log(db, ENTITY_TYPE, supplier.id, "updated", actor_id, changes)
    return supplier


def set_ai_systems(
    db: Session, supplier_id: int, ai_system_row_ids: list[int], actor_id: int | None
) -> Supplier:
    supplier = _get_or_raise(db, supplier_id)
    _validate_ai_system_rows(db, ai_system_row_ids)
    supplier_repository.replace_links(db, supplier_id, ai_system_row_ids)
    audit_service.log(
        db,
        ENTITY_TYPE,
        supplier_id,
        "ai_systems_updated",
        actor_id,
        {"ai_system_row_ids": sorted(set(ai_system_row_ids))},
    )
    return supplier


def linked_ai_system_ids(db: Session, supplier_id: int) -> list[int]:
    return [
        link.ai_system_row_id
        for link in supplier_repository.list_links_for_supplier(db, supplier_id)
    ]


def unlink_ai_system(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    """Drops every supplier's link to an AI system being deleted. The
    suppliers themselves survive -- they're organizational relationships
    that outlive any one system, like datasets."""
    links = supplier_repository.list_links_for_ai_system(db, ai_system_row_id)
    if not links:
        return
    supplier_repository.delete_links(db, links)
    for link in links:
        audit_service.log(
            db,
            ENTITY_TYPE,
            link.supplier_id,
            "ai_system_unlinked",
            actor_id,
            {"ai_system_row_id": ai_system_row_id},
        )


def record_review(
    db: Session,
    supplier_id: int,
    data: SupplierReviewCreate,
    actor_id: int | None,
    today: date | None = None,
) -> SupplierReview:
    _get_or_raise(db, supplier_id)
    if data.review_date > _today(today):
        raise ValidationError("A review can't be dated in the future.")
    review = supplier_repository.create_review(
        db,
        SupplierReview(
            supplier_id=supplier_id,
            review_date=data.review_date,
            outcome=data.outcome,
            notes=data.notes,
            reviewed_by=actor_id,
        ),
    )
    audit_service.log(
        db,
        ENTITY_TYPE,
        supplier_id,
        "review_recorded",
        actor_id,
        {"review_id": review.id, "review_date": review.review_date, "outcome": review.outcome},
    )
    return review


def delete_review(db: Session, review_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope, matching
    # corrective_action_service: evidence_service imports services back.
    from app.services import evidence_service

    review = supplier_repository.get_review(db, review_id)
    if review is None:
        raise NotFoundError("SupplierReview", review_id)
    supplier_id = review.supplier_id
    evidence_service.delete_all_for_entity(db, REVIEW_ENTITY_TYPE, review_id)
    supplier_repository.delete_review(db, review)
    audit_service.log(
        db, ENTITY_TYPE, supplier_id, "review_deleted", actor_id, {"review_id": review_id}
    )


def delete_supplier(db: Session, supplier_id: int, actor_id: int | None) -> None:
    from app.services import evidence_service

    supplier = _get_or_raise(db, supplier_id)
    for review in supplier_repository.list_reviews_for_supplier(db, supplier_id):
        evidence_service.delete_all_for_entity(db, REVIEW_ENTITY_TYPE, review.id)
        supplier_repository.delete_review(db, review)
    supplier_repository.delete_links(
        db, supplier_repository.list_links_for_supplier(db, supplier_id)
    )
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, supplier_id)
    framework_service.delete_tags(db, ENTITY_TYPE, supplier_id)
    supplier_repository.delete(db, supplier)
    audit_service.log(db, ENTITY_TYPE, supplier_id, "deleted", actor_id, {"name": supplier.name})
