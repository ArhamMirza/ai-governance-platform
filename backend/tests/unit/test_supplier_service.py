from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import sheet_repository, supplier_repository
from app.schemas.eu_ai_act import EuAiActApplicabilityUpdate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.schemas.supplier import (
    SupplierAISystemLinkUpdate,
    SupplierCreate,
    SupplierReviewCreate,
    SupplierUpdate,
)
from app.services import (
    ai_system_inventory_service,
    eu_ai_act_service,
    framework_service,
    risk_assessment_service,
    supplier_service,
)
from tests.helpers import complete_impact_assessment_db

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


# ---------- value-chain roles and Art. 25 ----------


def link(db: Session, supplier_id: int, row_id: int, **fields):
    return supplier_service.update_link(
        db, supplier_id, row_id, SupplierAISystemLinkUpdate(**fields), actor_id=None
    )


def assess_eu_ai_act(db: Session, **fields) -> None:
    eu_ai_act_service.update_settings(db, EuAiActApplicabilityUpdate(**fields), actor_id=None)


def test_any_art25_trigger_flags_the_link(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [row_id], actor_id=None)

    for trigger in ("rebranded", "substantially_modified", "repurposed_to_high_risk"):
        updated = link(db_session, supplier.id, row_id, **{trigger: True})
        assert updated.art25_triggered is True
    assert link(db_session, supplier.id, row_id, supplier_role="provider").art25_triggered is False


def test_updating_a_link_that_does_not_exist_is_refused(db_session: Session) -> None:
    supplier = make_supplier(db_session)

    with pytest.raises(NotFoundError):
        link(db_session, supplier.id, make_ai_system(db_session), supplier_role="provider")


def test_relinking_keeps_the_roles_already_recorded(db_session: Session) -> None:
    kept, dropped = make_ai_system(db_session, "Kept"), make_ai_system(db_session, "Dropped")
    added = make_ai_system(db_session, "Added")
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [kept, dropped], actor_id=None)
    link(db_session, supplier.id, kept, supplier_role="provider", rebranded=True)

    supplier_service.set_ai_systems(db_session, supplier.id, [kept, added], actor_id=None)

    links = {
        lnk.ai_system_row_id: lnk
        for lnk in supplier_service.links_for_supplier(db_session, supplier.id)
    }
    assert set(links) == {kept, added}
    assert (links[kept].supplier_role, links[kept].rebranded) == ("provider", True)
    assert links[added].supplier_role is None


def test_art25_alert_counts_triggered_links_until_the_org_is_a_provider(
    db_session: Session,
) -> None:
    row_id = make_ai_system(db_session)
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [row_id], actor_id=None)
    assert supplier_service.possible_provider_count(db_session) == 0

    link(db_session, supplier.id, row_id, rebranded=True)
    assert supplier_service.possible_provider_count(db_session) == 1  # not assessed

    assess_eu_ai_act(db_session, in_scope=True, is_deployer=True, has_high_risk_systems=True)
    assert supplier_service.possible_provider_count(db_session) == 1  # deployer only

    assess_eu_ai_act(
        db_session, in_scope=True, is_deployer=True, is_provider=True, has_high_risk_systems=True
    )
    assert supplier_service.possible_provider_count(db_session) == 0


def test_art25_alert_is_silent_out_of_scope(db_session: Session) -> None:
    row_id = make_ai_system(db_session)
    supplier = make_supplier(db_session)
    supplier_service.set_ai_systems(db_session, supplier.id, [row_id], actor_id=None)
    link(db_session, supplier.id, row_id, substantially_modified=True)

    assess_eu_ai_act(db_session, in_scope=False, scope_justification="No EU nexus.")

    assert supplier_service.possible_provider_count(db_session) == 0


# ---------- risk items naming a supplier ----------


def make_assessed_system_with_risk(db: Session, supplier_id: int) -> tuple[int, int]:
    """An AI system with a risk assessment holding one risk item that
    names the supplier. Returns (assessment id, row id)."""
    row_id = make_ai_system(db, "Assessed")
    complete_impact_assessment_db(db, row_id)
    assessment = risk_assessment_service.create_risk_assessment(
        db, RiskAssessmentCreate(ai_system_row_id=row_id), actor_id=None
    )
    risk_row = risk_assessment_service.add_row(
        db,
        assessment.id,
        {"category": "Third party", "description": "Model swap", "supplier_id": str(supplier_id)},
        actor_id=None,
    )
    return assessment.id, risk_row.id


def test_a_supplier_lists_the_risk_items_naming_it(db_session: Session, make_user) -> None:
    make_user()
    supplier = make_supplier(db_session)
    other = make_supplier(db_session, name="Other Co")
    assessment_id, row_id = make_assessed_system_with_risk(db_session, supplier.id)

    items = supplier_service.risk_items_for_supplier(db_session, supplier.id)

    assert [(i.risk_assessment_id, i.row_id, i.category) for i in items] == [
        (assessment_id, row_id, "Third party")
    ]
    assert supplier_service.risk_items_for_supplier(db_session, other.id) == []


def test_deleting_a_supplier_clears_risk_items_naming_it(db_session: Session, make_user) -> None:
    make_user()
    supplier = make_supplier(db_session)
    _, row_id = make_assessed_system_with_risk(db_session, supplier.id)

    supplier_service.delete_supplier(db_session, supplier.id, actor_id=None)

    row = sheet_repository.get_row(db_session, row_id)
    assert "supplier_id" not in row.data
    assert row.data["description"] == "Model swap"
