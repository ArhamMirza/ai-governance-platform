"""Suggesting which framework controls a record's own text relates to.

Deliberately not an LLM feature. Choosing among a small, fixed set of ~90
controls is a closed-set classification, not open-ended writing -- exactly
what this app's own document-search embeddings already do well, at no
per-call cost and with nothing leaving the machine. See app.core.embeddings
(BAAI/bge-small-en-v1.5, local, CPU) for the model itself.

Deliberately skips the sqlite-vec index retrieval_service.py uses for
document chunks, too. That index exists because a document search may be
ranking thousands of chunks and needs an approximate-nearest-neighbour
structure to do it fast, and because sqlite-vec is a loadable extension that
can fail to load on some Python builds. Neither problem exists here: there
are only ~90 controls, so a brute-force cosine comparison is microseconds,
and it never depends on sqlite-vec loading at all -- this works on every
machine app.core.embeddings itself works on.

No threshold here is empirically calibrated the way retrieval_service's
MAX_VECTOR_DISTANCE is (that one was measured against a real corpus of
questions and passages -- see its own comment). There is no equivalent
labelled corpus of "record text -> correct controls" to measure against, and
building one is exactly the training-data problem a supervised classifier
would also run into. So rather than invent a precise-looking number this
uses the loosest floor that still means something -- similarity above zero,
i.e. more alike than unrelated -- plus a generous top-N cap on top of it.
That still means a record whose text resembles nothing (every control comes
back no more similar than chance) suggests nothing, rather than always
handing back its "top 8" regardless of whether any of them fit; but it
never pretends to a precision this hasn't been measured for. A false
positive that does clear the floor costs a person one unchecked box in a
review screen, not a fabricated citation in an answer, which is what
justified spending the calibration effort in retrieval_service.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import embeddings
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.models.framework_control import FrameworkControl
from app.models.impact_assessment import ImpactAssessment
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.repositories import framework_control_repository

# Deliberately generous -- see module docstring. A person reviews the
# suggestions before anything is tagged, so over-suggesting costs one
# unchecked box; under-suggesting costs a control nobody ever sees offered.
TOP_N = 8

# The loosest floor that still means something: more alike than unrelated
# text would be by chance. Not tuned against any measured corpus -- see the
# module docstring for why -- so it exists to catch the "nothing here is
# even remotely related" case, not to draw a precise relevance line.
MIN_SIMILARITY = 0.0

_NARRATIVE_FIELDS = (
    "system_description",
    "intended_purpose",
    "foreseeable_misuse",
    "data_and_model_info",
    "deployment_environment",
    "affected_interested_parties",
    "human_oversight_role",
    "conclusion",
)


def _policy_text(db: Session, entity_id: int) -> str | None:
    record = db.get(Policy, entity_id)
    if record is None:
        return None
    return " ".join(part for part in (record.title, record.description) if part)


def _procedure_text(db: Session, entity_id: int) -> str | None:
    record = db.get(Procedure, entity_id)
    if record is None:
        return None
    return " ".join(part for part in (record.title, record.description) if part)


def _impact_assessment_text(db: Session, entity_id: int) -> str | None:
    record = db.get(ImpactAssessment, entity_id)
    if record is None:
        return None
    parts = [getattr(record, field) for field in _NARRATIVE_FIELDS]
    return " ".join(part for part in parts if part)


# Entity types this can gather substantive text for. Evidence (a filename)
# and AI system inventory rows (not yet wired to a tag picker in the UI) are
# deliberately not included here -- narrower to start, same as every other
# AI-assist feature in this app.
_TEXT_RESOLVERS = {
    "Policy": _policy_text,
    "Procedure": _procedure_text,
    "ImpactAssessment": _impact_assessment_text,
}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class _Scored:
    control: FrameworkControl
    similarity: float


def suggest_controls(db: Session, entity_type: str, entity_id: int) -> list[FrameworkControl]:
    """The controls this record's own text most resembles, most similar
    first. Empty if the record has no text yet, or if nothing clears the
    generous similarity bar -- never a top-N regardless of relevance."""
    resolver = _TEXT_RESOLVERS.get(entity_type)
    if resolver is None:
        raise ValidationError(
            f"Can't suggest framework controls for a {entity_type} -- "
            "tag it by hand instead."
        )
    text = resolver(db, entity_id)
    if text is None:
        raise NotFoundError(entity_type, entity_id)
    if not text.strip():
        return []

    controls = framework_control_repository.list_all(db)
    if not controls:
        return []

    control_vectors = embeddings.embed_passages(
        [f"{control.title}. {control.description or ''}" for control in controls]
    )
    record_vector = embeddings.embed_query(text)
    if not control_vectors or record_vector is None:
        raise ServiceUnavailableError(
            "Suggesting controls needs the local embedding model, which isn't "
            "available in this environment."
        )

    scored = sorted(
        (
            _Scored(control, _cosine_similarity(record_vector, vector))
            for control, vector in zip(controls, control_vectors, strict=True)
        ),
        key=lambda s: s.similarity,
        reverse=True,
    )
    return [s.control for s in scored if s.similarity > MIN_SIMILARITY][:TOP_N]
