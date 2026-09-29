from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import supplier_repository
from app.schemas.supplier import SupplierCreate, SupplierReviewCreate, SupplierUpdate
from app.services import ai_system_inventory_service, framework_service, supplier_service

TODAY = date(2026, 6, 15)


def make_ai_system(db: Session, name: str = "Resume Screener") -> int:
    return ai_system_inventory_service.add_row(db, {"name": name}, actor_id=None).id


def make_supplier(db: Session, **overrides):
    data = {"name": "Acme Models", "supplier_type": "model_provider"}
    data.update(overrides)
    return supplier_service.create_supplier(db, SupplierCreate(**data), actor_id=None)


def test_create_starts_active_with_nothing_due(db_session: Session) -> None:
    supplier = make_supplier(db_session)

    assert supplier.status == "active"
    standing = supplier_service.standing(supplier, [], TODAY)
    assert (standing.next_review_due, standing.review_overdue, standing.contract_status) == (
        None,
        False,
        None,
    )


def test_a_review_interval_needs_a_first_review_date(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        make_supplier(db_session, review_interval_months=12)


def test_a_partial_update_cannot_leave_the_schedule_half_set(db_session: Session) -> None:
    supplier = make_supplier(
        db_session, review_interval_months=12, first_review_due=date(2026, 7, 1)
    )

    with pytest.raises(ValidationError):
        supplier_service.update_supplier(
            db_session, supplier.id, SupplierUpdate(first_review_due=None), actor_id=None
        )

    assert supplier_service.get_supplier(db_session, supplier.id).first_review_due == date(
        2026, 7, 1
    )


def test_a_contract_cannot_end_before_it_starts(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        make_supplier(db_session, contract_start=date(2026, 6, 1), contract_end=date(2026, 5, 1))


def test_linking_ai_systems_replaces_the_set(db_session: Session) -> None:
    first, second = make_ai_system(db_session, "A"), make_ai_system(db_session, "B")
    supplier = make_supplier(db_session)

    supplier_service.set_ai_systems(db_session, supplier.id, [first, second], actor_id=None)
    supplier_service.set_ai_systems(db_session, supplier.id, [second], actor_id=None)

    assert supplier_service.linked_ai_system_ids(db_session, supplier.id) == [second]
    assert [s.id for s in supplier_service.list_suppliers(db_session, first)] == []
    assert [s.id for s in supplier_service.list_suppliers(db_session, second)] == [supplier.id]


def test_linking_an_unknown_ai_system_is_refused(db_session: Session) -> None:
    supplier = make_supplier(db_session)

    with pytest.raises(NotFoundError):
        supplier_service.set_ai_systems(db_session, supplier.id, [9999], actor_id=None)


def test_deleting_an_ai_system_unlinks_it_without_deleting_the_supplier(
    db_session: Session,
) -> None:
    row_id = make_ai_system(db_session)
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [row_id], actor_id=None)

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    assert supplier_service.get_supplier(db_session, supplier.id).name == "Acme Models"
    assert supplier_service.linked_ai_system_ids(db_session, supplier.id) == []


def test_a_review_moves_the_next_due_date_on(db_session: Session) -> None:
    supplier = make_supplier(
        db_session, review_interval_months=12, first_review_due=date(2026, 1, 1)
    )
    assert supplier_service.standing(supplier, [], TODAY).review_overdue is True

    review = supplier_service.record_review(
        db_session,
        supplier.id,
        SupplierReviewCreate(review_date=date(2026, 6, 1), outcome="concerns"),
        actor_id=None,
        today=TODAY,
    )

    standing = supplier_service.standing(supplier, [review.review_date], TODAY)
    assert standing.review_overdue is False
    assert standing.next_review_due == date(2027, 6, 1)


def test_a_review_cannot_be_dated_in_the_future(db_session: Session) -> None:
    supplier = make_supplier(db_session)

    with pytest.raises(ValidationError):
        supplier_service.record_review(
            db_session,
            supplier.id,
            SupplierReviewCreate(review_date=date(2026, 6, 16)),
            actor_id=None,
            today=TODAY,
        )


def test_deleting_a_supplier_removes_its_reviews_links_and_tags(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [row_id], actor_id=None)
    review = supplier_service.record_review(
        db_session,
        supplier.id,
        SupplierReviewCreate(review_date=date(2026, 6, 1)),
        actor_id=None,
        today=TODAY,
    )
    framework_service.set_tags(
        db_session, supplier_service.ENTITY_TYPE, supplier.id, [1], actor_id=None
    )

    supplier_service.delete_supplier(db_session, supplier.id, actor_id=None)

    assert supplier_repository.get_review(db_session, review.id) is None
    assert supplier_repository.list_links_for_ai_system(db_session, row_id) == []
    assert framework_service.get_tags(db_session, supplier_service.ENTITY_TYPE, supplier.id) == []
