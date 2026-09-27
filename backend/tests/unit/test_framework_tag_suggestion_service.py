"""Suggesting framework controls from a record's own text -- via the
embedding index, never an LLM. The suite's own local_models_are_stubbed
fixture (see conftest.py) replaces the real embedder with a deterministic
hashing vectoriser that puts texts sharing vocabulary near each other: this
exercises every line of the ranking path without pretending the stub
understands semantics no test here could actually demonstrate."""

import pytest
from sqlalchemy.orm import Session

from app.core import embeddings
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.repositories import framework_control_repository
from app.schemas.impact_assessment import ImpactAssessmentUpdate
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.services import (
    ai_system_inventory_service,
    framework_tag_suggestion_service,
    impact_assessment_service,
    policy_service,
    procedure_service,
)


def make_policy(
    db: Session, title: str = "Data Retention Policy", description: str | None = "x"
) -> int:
    return policy_service.create_policy(
        db, PolicyCreate(title=title, description=description), actor_id=None
    ).id


def make_procedure(db: Session, title: str, description: str | None) -> int:
    return procedure_service.create_procedure(
        db, ProcedureCreate(title=title, description=description), actor_id=None
    ).id


def make_impact_assessment(db: Session, **narrative) -> int:
    row = ai_system_inventory_service.add_row(db, {"name": "System"}, actor_id=None)
    from app.schemas.impact_assessment import ImpactAssessmentCreate

    assessment = impact_assessment_service.create_for_ai_system(
        db, row.id, ImpactAssessmentCreate(), actor_id=None
    )
    impact_assessment_service.update(
        db, assessment.id, ImpactAssessmentUpdate(**narrative), actor_id=None
    )
    return assessment.id


def codes(controls) -> list[str]:
    return [c.code for c in controls]


# ---------- ranking by shared vocabulary ----------


def test_suggests_the_control_whose_text_most_overlaps_the_policys(db_session: Session) -> None:
    policy_id = make_policy(
        db_session,
        title="AI risk management system",
        description=(
            "Establish, implement, document and maintain a risk management system "
            "for high-risk AI systems."
        ),
    )

    suggestions = framework_tag_suggestion_service.suggest_controls(db_session, "Policy", policy_id)

    assert suggestions, "expected at least one suggestion for closely-matching text"
    assert suggestions[0].code == "Art.9"


def test_a_procedures_text_is_used_the_same_way(db_session: Session) -> None:
    procedure_id = make_procedure(
        db_session,
        title="Data governance procedure",
        description="Training, validation and testing data sets shall be subject to "
        "appropriate data governance practices.",
    )

    suggestions = framework_tag_suggestion_service.suggest_controls(
        db_session, "Procedure", procedure_id
    )

    assert codes(suggestions)[:1] == ["Art.10"]


def test_an_impact_assessments_narrative_fields_are_combined(db_session: Session) -> None:
    assessment_id = make_impact_assessment(
        db_session,
        system_description="A model that assesses the impacts an AI system can have on "
        "individuals or groups of individuals, or both, and society.",
    )

    suggestions = framework_tag_suggestion_service.suggest_controls(
        db_session, "ImpactAssessment", assessment_id
    )

    assert "8.4" in codes(suggestions)


# ---------- the floor and the cap ----------


def test_never_returns_more_than_top_n(db_session: Session) -> None:
    policy_id = make_policy(
        db_session,
        title="AI policy",
        description="Establish an AI policy appropriate to the purpose of the organization.",
    )

    suggestions = framework_tag_suggestion_service.suggest_controls(db_session, "Policy", policy_id)

    assert len(suggestions) <= framework_tag_suggestion_service.TOP_N


def test_controls_with_negative_similarity_are_excluded_by_the_floor_not_just_the_cap(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The floor is exercised with synthetic vectors, not natural-language
    "gibberish" -- the hashing stub only has embeddings.DIMENSIONS (384)
    buckets, and real English words collide into shared buckets by chance
    often enough that no wording reliably produces "similar to nothing," so
    asserting that from real text would test the stub's luck, not the floor.

    Deliberately set up so the floor and the TOP_N cap would disagree if the
    floor didn't exist: only one control gets positive similarity, and every
    other control (far more than TOP_N of them) gets negative similarity --
    so without a floor, the cap alone would still fill out to TOP_N entries
    from the negative ones. Only the floor can make this return exactly one.
    """
    policy_id = make_policy(db_session)
    controls = framework_control_repository.list_all(db_session)
    assert len(controls) > framework_tag_suggestion_service.TOP_N
    dimensions = embeddings.DIMENSIONS

    def fake_passages(_texts: list[str]) -> list[list[float]]:
        vectors = []
        for i in range(len(controls)):
            vector = [0.0] * dimensions
            vector[0] = 1.0 if i == 0 else -1.0
            vectors.append(vector)
        return vectors

    def fake_query(_text: str) -> list[float]:
        vector = [0.0] * dimensions
        vector[0] = 1.0
        return vector

    monkeypatch.setattr(embeddings, "embed_passages", fake_passages)
    monkeypatch.setattr(embeddings, "embed_query", fake_query)

    suggestions = framework_tag_suggestion_service.suggest_controls(db_session, "Policy", policy_id)

    assert [c.id for c in suggestions] == [controls[0].id]


def test_a_record_with_no_text_yet_suggests_nothing_without_calling_the_embedder(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_id = make_policy(db_session, title="", description=None)
    called = False

    def fail(*_args, **_kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(embeddings, "embed_passages", fail)

    suggestions = framework_tag_suggestion_service.suggest_controls(db_session, "Policy", policy_id)

    assert suggestions == []
    assert called is False


# ---------- errors ----------


def test_an_unsupported_entity_type_is_rejected(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        framework_tag_suggestion_service.suggest_controls(db_session, "Evidence", 1)


def test_a_missing_record_is_reported_as_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        framework_tag_suggestion_service.suggest_controls(db_session, "Policy", 999_999)


def test_raises_when_the_embedding_model_is_unavailable(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_id = make_policy(db_session)
    monkeypatch.setattr(embeddings, "embed_query", lambda text: None)

    with pytest.raises(ServiceUnavailableError):
        framework_tag_suggestion_service.suggest_controls(db_session, "Policy", policy_id)
