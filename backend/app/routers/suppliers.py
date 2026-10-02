from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.supplier import Supplier
from app.models.supplier_ai_system import SupplierAISystem
from app.schemas.supplier import (
    SupplierAISystemLinkRead,
    SupplierAISystemLinkUpdate,
    SupplierAISystemsUpdate,
    SupplierCreate,
    SupplierDetailRead,
    SupplierRead,
    SupplierReviewCreate,
    SupplierReviewRead,
    SupplierRiskItemRead,
    SupplierUpdate,
)
from app.services import framework_service, supplier_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _to_read(
    db: Session, supplier: Supplier, review_dates: list, links: list[SupplierAISystem]
) -> SupplierRead:
    standing = supplier_service.standing(supplier, review_dates)
    return SupplierRead(
        id=supplier.id,
        name=supplier.name,
        supplier_type=supplier.supplier_type,
        description=supplier.description,
        status=supplier.status,
        owner_id=supplier.owner_id,
        contact_name=supplier.contact_name,
        contact_email=supplier.contact_email,
        contract_reference=supplier.contract_reference,
        contract_start=supplier.contract_start,
        contract_end=supplier.contract_end,
        responsibilities=supplier.responsibilities,
        requirements=supplier.requirements,
        review_interval_months=supplier.review_interval_months,
        first_review_due=supplier.first_review_due,
        ai_system_row_ids=[link.ai_system_row_id for link in links],
        ai_system_links=[SupplierAISystemLinkRead.model_validate(link) for link in links],
        next_review_due=standing.next_review_due,
        review_overdue=standing.review_overdue,
        contract_status=standing.contract_status,
        framework_tags=framework_service.get_tags(db, supplier_service.ENTITY_TYPE, supplier.id),
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
    )


def _to_detail(db: Session, supplier: Supplier) -> SupplierDetailRead:
    reviews = supplier_service.list_reviews(db, supplier.id)
    base = _to_read(
        db,
        supplier,
        [review.review_date for review in reviews],
        supplier_service.links_for_supplier(db, supplier.id),
    )
    return SupplierDetailRead(
        **base.model_dump(),
        reviews=[SupplierReviewRead.model_validate(review) for review in reviews],
    )


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    ai_system_row_id: int | None = None, db: Session = Depends(get_db)
) -> list[SupplierRead]:
    review_dates = supplier_service.review_dates_by_supplier(db)
    links = supplier_service.links_by_supplier(db)
    return [
        _to_read(db, supplier, review_dates[supplier.id], links[supplier.id])
        for supplier in supplier_service.list_suppliers(db, ai_system_row_id)
    ]


@router.post("", response_model=SupplierDetailRead, status_code=201)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SupplierDetailRead:
    return _to_detail(db, supplier_service.create_supplier(db, data, actor_id))


# Declared before the /{supplier_id} routes: otherwise DELETE /reviews/5
# matches DELETE /{supplier_id} first and fails its int validation.
@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    supplier_service.delete_review(db, review_id, actor_id)


@router.get("/{supplier_id}", response_model=SupplierDetailRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> SupplierDetailRead:
    return _to_detail(db, supplier_service.get_supplier(db, supplier_id))


@router.put("/{supplier_id}", response_model=SupplierDetailRead)
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SupplierDetailRead:
    return _to_detail(db, supplier_service.update_supplier(db, supplier_id, data, actor_id))


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    supplier_service.delete_supplier(db, supplier_id, actor_id)


@router.put("/{supplier_id}/ai-systems", response_model=SupplierDetailRead)
def set_ai_systems(
    supplier_id: int,
    data: SupplierAISystemsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SupplierDetailRead:
    supplier = supplier_service.set_ai_systems(db, supplier_id, data.ai_system_row_ids, actor_id)
    return _to_detail(db, supplier)


@router.put("/{supplier_id}/ai-systems/{ai_system_row_id}", response_model=SupplierDetailRead)
def update_ai_system_link(
    supplier_id: int,
    ai_system_row_id: int,
    data: SupplierAISystemLinkUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SupplierDetailRead:
    supplier_service.update_link(db, supplier_id, ai_system_row_id, data, actor_id)
    return _to_detail(db, supplier_service.get_supplier(db, supplier_id))


@router.get("/{supplier_id}/risk-items", response_model=list[SupplierRiskItemRead])
def list_risk_items(supplier_id: int, db: Session = Depends(get_db)) -> list[SupplierRiskItemRead]:
    return supplier_service.risk_items_for_supplier(db, supplier_id)


@router.post("/{supplier_id}/reviews", response_model=SupplierReviewRead, status_code=201)
def record_review(
    supplier_id: int,
    data: SupplierReviewCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SupplierReviewRead:
    review = supplier_service.record_review(db, supplier_id, data, actor_id)
    return SupplierReviewRead.model_validate(review)
