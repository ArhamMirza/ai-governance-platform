from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.models.supplier_ai_system import SupplierAISystem
from app.models.supplier_review import SupplierReview


def get(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def list_all(db: Session) -> list[Supplier]:
    return list(db.scalars(select(Supplier).order_by(Supplier.name, Supplier.id)))


def create(db: Session, supplier: Supplier) -> Supplier:
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def save(db: Session, supplier: Supplier) -> Supplier:
    db.commit()
    db.refresh(supplier)
    return supplier


def delete(db: Session, supplier: Supplier) -> None:
    db.delete(supplier)
    db.commit()


def get_review(db: Session, review_id: int) -> SupplierReview | None:
    return db.get(SupplierReview, review_id)


def list_reviews(db: Session) -> list[SupplierReview]:
    return list(db.scalars(select(SupplierReview).order_by(SupplierReview.id)))


def list_reviews_for_supplier(db: Session, supplier_id: int) -> list[SupplierReview]:
    return list(
        db.scalars(
            select(SupplierReview)
            .where(SupplierReview.supplier_id == supplier_id)
            .order_by(SupplierReview.review_date.desc(), SupplierReview.id.desc())
        )
    )


def create_review(db: Session, review: SupplierReview) -> SupplierReview:
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: SupplierReview) -> None:
    db.delete(review)
    db.commit()


def list_links(db: Session) -> list[SupplierAISystem]:
    return list(db.scalars(select(SupplierAISystem).order_by(SupplierAISystem.id)))


def list_links_for_supplier(db: Session, supplier_id: int) -> list[SupplierAISystem]:
    return list(
        db.scalars(
            select(SupplierAISystem)
            .where(SupplierAISystem.supplier_id == supplier_id)
            .order_by(SupplierAISystem.ai_system_row_id)
        )
    )


def list_links_for_ai_system(db: Session, ai_system_row_id: int) -> list[SupplierAISystem]:
    return list(
        db.scalars(
            select(SupplierAISystem)
            .where(SupplierAISystem.ai_system_row_id == ai_system_row_id)
            .order_by(SupplierAISystem.supplier_id)
        )
    )


def replace_links(db: Session, supplier_id: int, ai_system_row_ids: list[int]) -> None:
    """Swaps the supplier's links for exactly this set, in one commit."""
    for link in list_links_for_supplier(db, supplier_id):
        db.delete(link)
    db.flush()
    for row_id in sorted(set(ai_system_row_ids)):
        db.add(SupplierAISystem(supplier_id=supplier_id, ai_system_row_id=row_id))
    db.commit()


def delete_links(db: Session, links: list[SupplierAISystem]) -> None:
    for link in links:
        db.delete(link)
    db.commit()
