import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories import framework_control_repository
from app.services import framework_service


def iso_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001")[0].id


def eu_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "eu_ai_act")[0].id


def annex_a_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001", "annex_a_control")[0].id


def clause_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001", "clause")[0].id


def test_list_controls_filters_by_framework(db_session: Session) -> None:
    controls = framework_service.list_controls(db_session, "iso_42001")

    assert len(controls) > 0
    assert all(c.framework == "iso_42001" for c in controls)


def test_list_controls_orders_clauses_numerically_not_lexicographically(
    db_session: Session,
) -> None:
    """Regression: plain string ordering put "10.1" before "4.1" since
    "1" < "4" -- clauses must read in the order a human expects."""
    codes = [
        c.code for c in framework_control_repository.list_all(db_session, "iso_42001", "clause")
    ]

    assert codes.index("4.1") < codes.index("10.1")
    assert codes.index("9.3") < codes.index("10.1")


def test_list_controls_without_filter_returns_both_frameworks(db_session: Session) -> None:
    controls = framework_service.list_controls(db_session)

    frameworks = {c.framework for c in controls}
    assert frameworks == {"iso_42001", "eu_ai_act"}


def test_entity_starts_untagged(db_session: Session) -> None:
    assert framework_service.get_tags(db_session, "Policy", 1) == []


def test_set_tags_then_read_them_back(db_session: Session) -> None:
    control_id = iso_control_id(db_session)

    result = framework_service.set_tags(db_session, "Policy", 1, [control_id], actor_id=None)

    assert [c.id for c in result] == [control_id]
    assert [c.id for c in framework_service.get_tags(db_session, "Policy", 1)] == [control_id]


def test_set_tags_replaces_the_previous_set(db_session: Session) -> None:
    iso_id = iso_control_id(db_session)
    eu_id = eu_control_id(db_session)

    framework_service.set_tags(db_session, "Policy", 1, [iso_id], actor_id=None)
    framework_service.set_tags(db_session, "Policy", 1, [eu_id], actor_id=None)

    tags = framework_service.get_tags(db_session, "Policy", 1)
    assert [c.id for c in tags] == [eu_id]


def test_set_tags_with_an_overlapping_id_does_not_violate_the_unique_constraint(
    db_session: Session,
) -> None:
    """Regression: re-saving a set that keeps one existing tag and adds
    another used to hit the (entity_type, entity_id, control_id) unique
    constraint, because the new inserts could flush before the old rows'
    deletes."""
    iso_id = iso_control_id(db_session)
    eu_id = eu_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", 1, [iso_id], actor_id=None)

    result = framework_service.set_tags(db_session, "Policy", 1, [iso_id, eu_id], actor_id=None)

    assert {c.id for c in result} == {iso_id, eu_id}


def test_set_tags_to_empty_list_clears_them(db_session: Session) -> None:
    control_id = iso_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", 1, [control_id], actor_id=None)

    framework_service.set_tags(db_session, "Policy", 1, [], actor_id=None)

    assert framework_service.get_tags(db_session, "Policy", 1) == []


def test_set_tags_deduplicates_ids(db_session: Session) -> None:
    control_id = iso_control_id(db_session)

    result = framework_service.set_tags(
        db_session, "Policy", 1, [control_id, control_id], actor_id=None
    )

    assert len(result) == 1


def test_set_tags_rejects_unknown_control_id(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        framework_service.set_tags(db_session, "Policy", 1, [999999], actor_id=None)


def test_tags_are_scoped_per_entity(db_session: Session) -> None:
    iso_id = iso_control_id(db_session)
    eu_id = eu_control_id(db_session)

    framework_service.set_tags(db_session, "Policy", 1, [iso_id], actor_id=None)
    framework_service.set_tags(db_session, "Policy", 2, [eu_id], actor_id=None)

    assert [c.id for c in framework_service.get_tags(db_session, "Policy", 1)] == [iso_id]
    assert [c.id for c in framework_service.get_tags(db_session, "Policy", 2)] == [eu_id]


def test_tags_are_scoped_per_entity_type(db_session: Session) -> None:
    control_id = iso_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", 1, [control_id], actor_id=None)

    assert framework_service.get_tags(db_session, "Procedure", 1) == []


def test_set_tags_is_audited(db_session: Session) -> None:
    from app.repositories import audit_log_repository

    control_id = iso_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", 7, [control_id], actor_id=None)

    entries = audit_log_repository.list_for_entity(db_session, "Policy", 7)
    assert [e.action for e in entries] == ["framework_tags_updated"]
    assert entries[0].diff == {"control_ids": [control_id]}


def test_delete_tags_removes_all_tags_for_the_entity(db_session: Session) -> None:
    control_id = iso_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", 1, [control_id], actor_id=None)

    framework_service.delete_tags(db_session, "Policy", 1)

    assert framework_service.get_tags(db_session, "Policy", 1) == []


def test_get_mapping_returns_all_clauses_and_articles_but_not_annex_a_controls(
    db_session: Session,
) -> None:
    entries = framework_service.get_mapping(db_session)

    categories = {e.category for e in entries}
    assert categories == {"clause", "annex_a_control"}
    assert len(entries) == 85


def test_get_mapping_filters_by_framework(db_session: Session) -> None:
    entries = framework_service.get_mapping(db_session, "eu_ai_act")

    assert len(entries) == 23
    assert all(e.framework == "eu_ai_act" for e in entries)


def test_get_mapping_lists_tagged_policy_by_title(db_session: Session) -> None:
    from app.models.policy import Policy

    policy = Policy(title="Data Retention Policy")
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    control_id = clause_control_id(db_session)
    framework_service.set_tags(db_session, "Policy", policy.id, [control_id], actor_id=None)

    entries = framework_service.get_mapping(db_session)
    entry = next(e for e in entries if e.id == control_id)
    assert len(entry.tagged_items) == 1
    assert entry.tagged_items[0].entity_type == "Policy"
    assert entry.tagged_items[0].entity_id == policy.id
    assert entry.tagged_items[0].label == "Data Retention Policy"


def test_get_mapping_falls_back_to_a_generic_label_for_an_unknown_entity_type(
    db_session: Session,
) -> None:
    """A type with no label rule still shows -- not knowing how to name
    something isn't a reason to hide real coverage."""
    control_id = clause_control_id(db_session)
    framework_service.set_tags(db_session, "SomeFutureThing", 7, [control_id], actor_id=None)

    entries = framework_service.get_mapping(db_session)
    entry = next(e for e in entries if e.id == control_id)
    assert entry.tagged_items[0].label == "SomeFutureThing #7"


def test_get_mapping_drops_a_tag_whose_record_is_gone(db_session: Session) -> None:
    """These views are read as evidence that a control is covered, so a tag
    pointing at something deleted must not render as though it were real."""
    control_id = clause_control_id(db_session)
    framework_service.set_tags(db_session, "RiskAssessment", 999, [control_id], actor_id=None)

    entries = framework_service.get_mapping(db_session)
    entry = next(e for e in entries if e.id == control_id)
    assert entry.tagged_items == []


def test_get_soa_lists_only_annex_a_controls_defaulting_to_applicable(
    db_session: Session,
) -> None:
    entries = framework_service.get_soa(db_session)

    assert len(entries) == 38
    assert all(e.applicability == "applicable" for e in entries)
    assert all(e.justification is None for e in entries)


def test_update_soa_entry_sets_not_applicable_with_justification(db_session: Session) -> None:
    control_id = annex_a_control_id(db_session)

    updated = framework_service.update_soa_entry(
        db_session, control_id, "not_applicable", "Not used by this organization.", actor_id=None
    )

    assert updated.applicability == "not_applicable"
    assert updated.justification == "Not used by this organization."

    entries = framework_service.get_soa(db_session)
    entry = next(e for e in entries if e.id == control_id)
    assert entry.applicability == "not_applicable"
    assert entry.justification == "Not used by this organization."


def test_update_soa_entry_rejects_invalid_applicability(db_session: Session) -> None:
    control_id = annex_a_control_id(db_session)

    with pytest.raises(ValidationError):
        framework_service.update_soa_entry(
            db_session, control_id, "sort_of", None, actor_id=None
        )


def test_update_soa_entry_rejects_a_clause_that_is_not_an_annex_a_control(
    db_session: Session,
) -> None:
    control_id = clause_control_id(db_session)

    with pytest.raises(NotFoundError):
        framework_service.update_soa_entry(
            db_session, control_id, "applicable", None, actor_id=None
        )


def test_update_soa_entry_is_audited(db_session: Session) -> None:
    from app.repositories import audit_log_repository

    control_id = annex_a_control_id(db_session)
    framework_service.update_soa_entry(
        db_session, control_id, "not_applicable", "Out of scope.", actor_id=None
    )

    entries = audit_log_repository.list_for_entity(db_session, "FrameworkSoaEntry", control_id)
    assert [e.action for e in entries] == ["framework_soa_updated"]
