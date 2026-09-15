"""Indexing the records themselves, not only the files attached to them.

A governance record is already structured, so the risk here is different
from a document's. Nothing fails to parse. What can go wrong is subtler: the
index drifts out of step with the record, and a stale index is invisible --
it looks exactly like a fresh one until someone searches for the thing that
changed and is told the old answer with full confidence.

So most of these tests are about staleness rather than extraction.
"""

from sqlalchemy.orm import Session

from app.models.document_chunk import SourceType
from app.models.impact_assessment import ImpactAssessment
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.models.sheet import Sheet, SheetRow
from app.services import document_index_service, record_rendering, retrieval_service
from tests.unit.test_document_indexing import chunks_of


def make_policy(db: Session, title: str = "Acceptable Use", **fields) -> Policy:
    policy = Policy(title=title, **fields)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def make_sheet_row(db: Session, entity_type: str, data: dict, columns=None) -> SheetRow:
    sheet = db.scalar(Sheet.__table__.select().where(Sheet.entity_type == entity_type))
    if sheet is None:
        new_sheet = Sheet(
            entity_type=entity_type,
            title=entity_type,
            columns=columns or [{"key": k, "label": k.replace("_", " ").title()} for k in data],
        )
        db.add(new_sheet)
        db.commit()
        db.refresh(new_sheet)
        sheet_id = new_sheet.id
    else:
        sheet_id = sheet.id
    row = SheetRow(sheet_id=sheet_id, row_index=0, data=data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def search_titles(db: Session, query: str) -> list[str]:
    return [c.source_title for c in retrieval_service.search(db, query).citations]


# ---------- what a record looks like once indexed ----------


def test_a_policy_record_is_searchable_without_any_document_attached(
    db_session: Session,
) -> None:
    """The record is the thing being governed. Until now only files
    uploaded against it could be found."""
    make_policy(db_session, title="Model Retraining Policy")

    document_index_service.drain(db_session)

    assert search_titles(db_session, "model retraining") == ["Policy: Model Retraining Policy"]


def test_a_record_keeps_its_values_exact_rather_than_paraphrasing_them(
    db_session: Session,
) -> None:
    """Keyword search is carried precisely so a score, an id or a date can
    be matched literally. Rendering a record into prose would lose that."""
    row = make_sheet_row(
        db_session,
        "RiskAssessment",
        {"title": "Biased shortlisting", "likelihood": "4", "impact": "5", "owner": "Ada"},
    )

    rendered = record_rendering.render(db_session, SourceType.RISK_ITEM, row.id)

    body = rendered.segments[0].text
    assert "Likelihood: 4" in body
    assert "Impact: 5" in body


def test_every_value_carries_its_label(db_session: Session) -> None:
    """A retrieved passage has to be readable on its own; a bare list of
    cells means nothing to the reader or the model."""
    row = make_sheet_row(
        db_session, "AISystemInventory", {"name": "Resume Screener", "purpose": "Rank applicants"}
    )

    rendered = record_rendering.render(db_session, SourceType.AI_SYSTEM, row.id)

    assert "Purpose: Rank applicants" in rendered.segments[0].text
    assert rendered.title == "AI system: Resume Screener"


def test_an_impact_assessment_is_split_so_a_citation_names_the_section(
    db_session: Session,
) -> None:
    """Eight long narratives as one passage would be one unretrievable blob,
    and a citation saying only "this assessment" helps nobody check it."""
    row = make_sheet_row(db_session, "AISystemInventory", {"name": "Resume Screener"})
    assessment = ImpactAssessment(
        ai_system_row_id=row.id,
        intended_purpose="Rank applicants by fit.",
        foreseeable_misuse="Using the ranking as an automatic rejection.",
    )
    db_session.add(assessment)
    db_session.commit()

    document_index_service.index_record(db_session, SourceType.IMPACT_ASSESSMENT, assessment.id)

    sections = {
        c.section for c in chunks_of(db_session, SourceType.IMPACT_ASSESSMENT, assessment.id)
    }
    assert "Intended purpose" in sections
    assert "Foreseeable misuse" in sections


def test_a_documents_chunk_still_says_which_record_it_belongs_to(
    db_session: Session, tmp_path
) -> None:
    """A file uploaded against a policy is not the policy, but a search for
    everything known about that policy has to return both."""
    from tests.unit.test_document_indexing import add_document

    evidence = add_document(db_session, tmp_path, "signed.txt", b"Signed by the CAIGO.")
    document_index_service.index_evidence(db_session, evidence.id)

    chunk = chunks_of(db_session, SourceType.EVIDENCE, evidence.id)[0]
    assert chunk.source_type == SourceType.EVIDENCE
    assert (chunk.entity_type, chunk.entity_id) == (evidence.entity_type, evidence.entity_id)


# ---------- staleness ----------


def test_editing_a_record_queues_it_without_anyone_remembering_to(
    db_session: Session,
) -> None:
    """Records are written from a dozen services and will be written from
    more. If keeping the index current meant calling something after each
    write, it would be right the day it was written and wrong within a
    month -- silently, because a stale index looks like a fresh one."""
    policy = make_policy(db_session)
    document_index_service.drain(db_session)
    assert document_index_service.queue_depth(db_session) == 0

    policy.description = "Covers third-party model use."
    db_session.commit()

    assert document_index_service.queue_depth(db_session) == 1


def test_a_search_answers_from_the_record_as_it_is_now(db_session: Session) -> None:
    # The old and new wordings share no vocabulary, so the second assertion
    # is really about the old text being gone rather than about a word the
    # replacement happens to reuse.
    policy = make_policy(db_session, description="Restricted to on-premise deployments.")
    assert search_titles(db_session, "premise deployments")

    policy.description = "Extended to third-party hosted inference."
    db_session.commit()

    assert search_titles(db_session, "third-party hosted inference")
    assert search_titles(db_session, "premise deployments") == []


def test_a_deleted_record_stops_being_searchable(db_session: Session) -> None:
    policy = make_policy(db_session, title="Temporary Policy")
    assert search_titles(db_session, "Temporary Policy")

    db_session.delete(policy)
    db_session.commit()

    assert search_titles(db_session, "Temporary Policy") == []


def test_a_record_edited_repeatedly_is_reindexed_once(db_session: Session) -> None:
    """A bulk import writes hundreds of rows; queueing each edit separately
    would mean reindexing the same row over and over from stale states."""
    policy = make_policy(db_session)
    document_index_service.drain(db_session)

    for n in range(5):
        policy.description = f"Revision {n}"
        db_session.commit()

    assert document_index_service.queue_depth(db_session) == 1


def test_a_factor_score_change_reindexes_its_assessment(db_session: Session) -> None:
    """The factor is not the record anyone searches for or cites -- the
    assessment is -- so the change has to reach the assessment's index."""
    from app.models.impact_factor_assessment import ImpactFactorAssessment

    row = make_sheet_row(db_session, "AISystemInventory", {"name": "Resume Screener"})
    assessment = ImpactAssessment(ai_system_row_id=row.id)
    db_session.add(assessment)
    db_session.commit()
    document_index_service.drain(db_session)

    db_session.add(
        ImpactFactorAssessment(
            impact_assessment_id=assessment.id, factor="Fairness", score=4,
            harms="Shortlisting may disadvantage career-break applicants.",
        )
    )
    db_session.commit()

    assert document_index_service.queue_depth(db_session) == 1
    document_index_service.drain(db_session)
    assert search_titles(db_session, "career-break applicants")


# ---------- the queue ----------


def test_draining_is_bounded_so_one_search_cannot_stall(db_session: Session) -> None:
    """A bulk import must not turn the next search into a long wait."""
    for n in range(document_index_service.DRAIN_BUDGET + 5):
        make_policy(db_session, title=f"Policy {n}")

    done = document_index_service.drain(db_session)

    assert sum(done.values()) == document_index_service.DRAIN_BUDGET
    assert document_index_service.queue_depth(db_session) == 5


def test_the_rest_of_the_queue_is_picked_up_by_the_next_drain(db_session: Session) -> None:
    for n in range(document_index_service.DRAIN_BUDGET + 5):
        make_policy(db_session, title=f"Policy {n}")

    document_index_service.drain(db_session)
    document_index_service.drain(db_session)

    assert document_index_service.queue_depth(db_session) == 0


def test_a_record_that_cannot_be_indexed_does_not_block_the_queue(
    db_session: Session, monkeypatch
) -> None:
    """One bad record stalling every other record forever would be a far
    worse failure than that record going unindexed."""
    make_policy(db_session, title="Bad Policy")
    make_policy(db_session, title="Good Policy")

    calls = {"n": 0}
    original = record_rendering.render

    def sometimes_explode(db, source_type, source_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("rendering fell over")
        return original(db, source_type, source_id)

    monkeypatch.setattr(record_rendering, "render", sometimes_explode)

    document_index_service.drain(db_session)

    assert document_index_service.queue_depth(db_session) == 0
    assert search_titles(db_session, "Good Policy")


def test_a_queued_record_that_has_since_been_deleted_is_handled(db_session: Session) -> None:
    policy = make_policy(db_session, title="Fleeting Policy")
    policy_id = policy.id
    db_session.delete(policy)
    db_session.commit()

    document_index_service.drain(db_session)

    assert chunks_of(db_session, SourceType.POLICY, policy_id) == []
    assert document_index_service.queue_depth(db_session) == 0


def test_searching_leaves_no_queued_work_behind_for_a_small_queue(
    db_session: Session,
) -> None:
    make_policy(db_session, title="Model Retraining Policy")

    retrieval_service.search(db_session, "model retraining")

    assert document_index_service.queue_depth(db_session) == 0


# ---------- documents and records share one index ----------


def test_one_search_returns_both_a_record_and_a_document(
    db_session: Session, tmp_path
) -> None:
    from tests.unit.test_document_indexing import add_document

    make_policy(db_session, title="Retention Policy", description="Applicant data is kept.")
    evidence = add_document(
        db_session, tmp_path, "retention-schedule.txt", b"Applicant data is kept for 24 months."
    )
    document_index_service.index_evidence(db_session, evidence.id)

    titles = search_titles(db_session, "applicant data kept")

    assert "Policy: Retention Policy" in titles
    assert "retention-schedule.txt" in titles


def test_a_procedure_record_is_indexed_too(db_session: Session) -> None:
    db_session.add(Procedure(title="Incident Response Procedure"))
    db_session.commit()

    document_index_service.drain(db_session)

    assert search_titles(db_session, "incident response") == [
        "Procedure: Incident Response Procedure"
    ]
