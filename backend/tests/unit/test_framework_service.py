import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories import framework_control_repository
from app.services import framework_service


def iso_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "iso_42001")[0].id


def eu_control_id(db: Session) -> int:
    return framework_control_repository.list_all(db, "eu_ai_act")[0].id


def test_list_controls_filters_by_framework(db_session: Session) -> None:
    controls = framework_service.list_controls(db_session, "iso_42001")

    assert len(controls) > 0
    assert all(c.framework == "iso_42001" for c in controls)


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
