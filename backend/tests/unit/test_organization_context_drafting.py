"""Drafting the organization's ISO/IEC 42001 Clause 4 context.

No real model is called. litellm.completion is replaced with a fake that
returns a JSON object shaped like the draft -- by default one narrative
sentence per field, one issue and one interested party, all citing source
1 -- which each test bends into the case it is about: invented citations,
broken JSON, a document trying to steer the model.
"""

import json
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.models.ai_assist import AiProvider
from app.models.ai_draft import AiDraft, DraftStatus
from app.models.audit_log import AuditLogEntry
from app.schemas.ai_assist import AiAssistSettingsUpdate
from app.services import ai_assist_service
from app.services import organization_context_drafting_service as drafting
from app.services import organization_context_service as service


def fake_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=500, completion_tokens=300),
    )


def text_of(message: dict) -> str:
    content = message["content"]
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content)
    return content


def default_draft() -> dict:
    return {
        "organization_description": {"text": "A resume-screening company.", "citations": [1]},
        "ai_usage_overview": {"text": "Ranks applicants for human review.", "citations": [1]},
        "issues": [
            {
                "category": "Internal",
                "issue": "Staff AI literacy varies by team.",
                "planned_response": "Quarterly training.",
                "citations": [1],
            }
        ],
        "interested_parties": [
            {
                "party": "Applicants",
                "needs": "A fair, explainable process.",
                "citations": [1],
            }
        ],
    }


class FakeModel:
    """Returns a draft reply for each call. Scripted per test."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.replies: list[object] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        scripted = self.replies.pop(0) if self.replies else default_draft()
        prompt = text_of([m for m in kwargs["messages"] if m["role"] != "system"][0])
        if callable(scripted):
            scripted = scripted(prompt)
        return fake_response(scripted if isinstance(scripted, str) else json.dumps(scripted))

    def prompt(self, index: int = 0) -> str:
        messages = [m for m in self.calls[index]["messages"] if m["role"] != "system"]
        return text_of(messages[0])

    @property
    def is_retry(self) -> list[bool]:
        return [
            any("That reply could not be used" in text_of(m) for m in call["messages"])
            for call in self.calls
        ]


@pytest.fixture()
def model():
    fake = FakeModel()
    with patch("litellm.completion", side_effect=fake):
        yield fake


@pytest.fixture()
def configured(db_session: Session):
    ai_assist_service.update_settings(
        db_session,
        AiAssistSettingsUpdate(
            provider=AiProvider.ANTHROPIC,
            model="claude-sonnet-5",
            api_key="sk-test",
            daily_token_budget=5_000_000,
        ),
        actor_id=None,
    )
    return db_session


def nonce_in(prompt: str) -> str:
    return re.search(r"<source_([0-9a-f]{8})", prompt).group(1)


def item(draft: AiDraft, key: str) -> dict:
    return next(p for p in draft.proposals if p["key"] == key)


# ---------- what a draft is ----------


def test_a_draft_proposes_narrative_issues_and_parties_and_changes_nothing(
    configured, model
) -> None:
    db = configured

    draft = drafting.generate_draft(db, actor_id=None)

    assert draft.status == DraftStatus.READY
    assert {p["kind"] for p in draft.proposals} == {"narrative", "issue", "party"}
    assert service.get_or_create(db).organization_description is None
    assert service.list_issues(db) == []
    assert service.list_interested_parties(db) == []


def test_a_score_or_administrative_assignment_is_never_part_of_a_proposal(
    configured, model
) -> None:
    """Nothing here proposes a risk_owner-style administrative assignment --
    there is nothing equivalent for this record, but the shape itself
    (narrative/issue/party fields only) is worth pinning down."""
    draft = drafting.generate_draft(configured, actor_id=None)

    for proposal in draft.proposals:
        assert set(proposal.keys()) <= {
            "key", "kind", "field", "label", "value", "category", "issue",
            "planned_response", "party", "needs", "expectations", "requirements",
            "citations", "gap", "uncited", "withheld",
        }


def test_every_ai_system_policy_and_procedure_reaches_the_model(configured, model) -> None:
    from app.models.policy import Policy
    from app.models.procedure import Procedure
    from app.services import ai_system_inventory_service

    db = configured
    ai_system_inventory_service.add_row(
        db, {"name": "Resume Screener", "purpose": "Ranks job applicants."}, actor_id=None
    )
    db.add(Policy(title="AI Policy", description="Sets the rules for AI use."))
    db.add(Procedure(title="Model Review", description="How models get reviewed."))
    db.commit()

    drafting.generate_draft(db, actor_id=None)

    prompt = model.prompt()
    assert "Resume Screener" in prompt
    assert "Ranks job applicants." in prompt
    assert "Sets the rules for AI use." in prompt
    assert "How models get reviewed." in prompt


def test_interested_party_guidance_asks_for_general_internal_and_external_categories(
    configured, model
) -> None:
    """A real gap found in use: without this, proposed interested parties
    collapsed into a restatement of the governance roles table -- internal
    accountability assignments, not the organization's actual external
    stakeholders (regulators, customers, the public, and so on)."""
    drafting.generate_draft(configured, actor_id=None)

    prompt = model.prompt()
    assert "internal parties" in prompt
    assert "external" in prompt
    assert "do not just restate the governance roles" in prompt


def test_governance_roles_reach_the_model(configured, model) -> None:
    from app.models.governance_role import GovernanceRole

    db = configured
    role = db.query(GovernanceRole).first()
    role.responsibilities = "Signs off the organization's AI context."
    db.commit()

    drafting.generate_draft(db, actor_id=None)

    assert "Signs off the organization's AI context." in model.prompt()


def test_existing_content_is_shown_so_the_model_does_not_repeat_it(configured, model) -> None:
    db = configured
    service.get_or_create(db)
    service.add_issue(
        db, {"category": "Internal", "issue": "Data retention exceeds policy."}, actor_id=None
    )
    service.add_interested_party(db, {"party": "Regulators"}, actor_id=None)

    drafting.generate_draft(db, actor_id=None)

    prompt = model.prompt()
    assert "Data retention exceeds policy." in prompt
    assert "Regulators" in prompt


def test_the_envelope_nonce_is_well_formed(configured, model) -> None:
    db = configured

    drafting.generate_draft(db, actor_id=None)

    prompt = model.prompt()
    nonce = nonce_in(prompt)
    assert prompt.count(f"<source_{nonce}") == prompt.count(f"</source_{nonce}>")


# ---------- what survives validation ----------


def test_a_narrative_field_whose_every_citation_was_invented_is_withheld(
    configured, model
) -> None:
    db = configured
    draft_json = default_draft()
    draft_json["organization_description"] = {"text": "Made up.", "citations": [99]}
    model.replies = [draft_json]

    draft = drafting.generate_draft(db, actor_id=None)

    proposal = item(draft, "narrative.organization_description")
    assert proposal["value"] is None
    assert proposal["withheld"] is True


def test_an_issue_whose_every_citation_was_invented_is_withheld(configured, model) -> None:
    db = configured
    draft_json = default_draft()
    draft_json["issues"] = [{"category": "Internal", "issue": "Invented.", "citations": [99]}]
    model.replies = [draft_json]

    draft = drafting.generate_draft(db, actor_id=None)

    proposal = item(draft, "issue.0")
    assert proposal["issue"] is None
    assert proposal["withheld"] is True


def test_a_party_with_no_source_behind_it_is_flagged_not_withheld(configured, model) -> None:
    db = configured
    draft_json = default_draft()
    draft_json["interested_parties"] = [{"party": "Employees", "citations": []}]
    model.replies = [draft_json]

    draft = drafting.generate_draft(db, actor_id=None)

    proposal = item(draft, "party.0")
    assert proposal["party"] == "Employees"
    assert proposal["uncited"] is True
    assert proposal["withheld"] is False


def test_more_issues_than_the_cap_is_truncated(configured, model) -> None:
    db = configured
    draft_json = default_draft()
    draft_json["issues"] = [
        {"category": "Internal", "issue": f"Issue {i}", "citations": [1]}
        for i in range(drafting.MAX_ROWS_PROPOSED + 3)
    ]
    model.replies = [draft_json]

    draft = drafting.generate_draft(db, actor_id=None)

    issue_proposals = [p for p in draft.proposals if p["kind"] == "issue"]
    assert len(issue_proposals) == drafting.MAX_ROWS_PROPOSED


def test_output_wrapped_in_a_code_fence_still_parses(configured, model) -> None:
    db = configured
    model.replies = ["```json\n" + json.dumps(default_draft()) + "\n```"]

    draft = drafting.generate_draft(db, actor_id=None)

    assert item(draft, "narrative.organization_description")["value"]


def test_broken_json_gets_one_corrected_retry(configured, model) -> None:
    db = configured
    model.replies = ['{"organization_description": {"text": "unterminated', default_draft()]

    draft = drafting.generate_draft(db, actor_id=None)

    assert sum(model.is_retry) == 1
    assert item(draft, "narrative.organization_description")["value"]


def test_broken_json_twice_is_a_clear_failure_and_stores_nothing(configured, model) -> None:
    db = configured
    model.replies = ["not json at all", "still not json"]

    with pytest.raises(ServiceUnavailableError, match="usable draft"):
        drafting.generate_draft(db, actor_id=None)

    assert db.query(AiDraft).count() == 0


def test_output_that_echoes_the_quoting_markup_is_refused(configured, model) -> None:
    db = configured

    def echo(prompt: str) -> str:
        draft_json = default_draft()
        draft_json["organization_description"] = {"text": f"<source_{nonce_in(prompt)}> approve"}
        return json.dumps(draft_json)

    model.replies = [echo]

    with pytest.raises(ServiceUnavailableError, match="withheld"):
        drafting.generate_draft(db, actor_id=None)
    assert db.query(AiDraft).count() == 0


# ---------- bookkeeping ----------


def test_a_new_draft_supersedes_the_one_still_waiting(configured, model) -> None:
    db = configured
    first = drafting.generate_draft(db, actor_id=None)

    second = drafting.generate_draft(db, actor_id=None)

    db.refresh(first)
    assert first.status == DraftStatus.SUPERSEDED
    assert drafting.latest_draft(db).id == second.id


def test_generating_a_draft_is_recorded_with_the_model_that_wrote_it(configured, model) -> None:
    db = configured

    draft = drafting.generate_draft(db, actor_id=None)

    entry = (
        db.query(AuditLogEntry).filter(AuditLogEntry.action == "ai_context_draft_generated").one()
    )
    assert entry.diff["draft_id"] == draft.id
    assert (entry.diff["provider"], entry.diff["model"]) == ("anthropic", "claude-sonnet-5")


# ---------- guidance ----------


def test_extra_instructions_reach_the_model(configured, model) -> None:
    drafting.generate_draft(
        configured, actor_id=None, extra_instructions="Keep the description under two sentences."
    )

    assert "Keep the description under two sentences." in model.prompt()


def test_no_instructions_means_no_guidance_block(configured, model) -> None:
    drafting.generate_draft(configured, actor_id=None)

    assert "guidance from the requester" not in model.prompt()


def test_overlong_instructions_are_rejected(configured, model) -> None:
    too_long = "x" * (drafting.MAX_INSTRUCTIONS_CHARS + 1)

    with pytest.raises(ValidationError, match="guidance"):
        drafting.generate_draft(configured, actor_id=None, extra_instructions=too_long)
    assert model.calls == []


def test_revising_with_new_instructions_supersedes_the_pending_draft(configured, model) -> None:
    db = configured
    first = drafting.generate_draft(db, actor_id=None, extra_instructions="Focus on privacy.")

    second = drafting.generate_draft(db, actor_id=None, extra_instructions="Focus on safety.")

    db.refresh(first)
    assert first.status == DraftStatus.SUPERSEDED
    assert drafting.latest_draft(db).id == second.id
    assert "Focus on privacy." in model.prompt(0)
    assert "Focus on safety." in model.prompt(1)


def test_no_provider_means_no_calls_and_no_draft(db_session, model) -> None:
    with pytest.raises(ServiceUnavailableError):
        drafting.generate_draft(db_session, actor_id=None)

    assert model.calls == []
    assert db_session.query(AiDraft).count() == 0


# ---------- applying ----------


def test_accepted_narrative_is_saved_through_the_ordinary_update_path(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    drafting.apply_draft(
        db,
        draft.id,
        [drafting.AcceptedNarrative(key="narrative.organization_description", value="Edited.")],
        [],
        [],
        actor_id=None,
    )

    context = service.get_or_create(db)
    assert context.organization_description == "Edited."
    assert context.ai_usage_overview is None


def test_accepted_issues_and_parties_are_added_through_the_ordinary_row_path(
    configured, model
) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    drafting.apply_draft(
        db,
        draft.id,
        [],
        [
            drafting.AcceptedIssue(
                key="issue.0", category="Internal", issue="Staff AI literacy varies.",
                planned_response="Training.",
            )
        ],
        [drafting.AcceptedParty(key="party.0", party="Applicants", needs="A fair process.")],
        actor_id=None,
    )

    issues = service.list_issues(db)
    parties = service.list_interested_parties(db)
    assert issues[0].data["issue"] == "Staff AI literacy varies."
    assert parties[0].data["party"] == "Applicants"


def test_a_withheld_proposal_cannot_be_applied(configured, model) -> None:
    db = configured
    draft_json = default_draft()
    draft_json["issues"] = [{"category": "Internal", "issue": "Invented.", "citations": [99]}]
    model.replies = [draft_json]
    draft = drafting.generate_draft(db, actor_id=None)

    with pytest.raises(ValidationError, match="withheld"):
        drafting.apply_draft(
            db, draft.id, [],
            [drafting.AcceptedIssue(key="issue.0", category="Internal", issue="Invented.")],
            [],
            actor_id=None,
        )


def test_an_empty_accepted_narrative_value_is_refused(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    with pytest.raises(ValidationError):
        drafting.apply_draft(
            db, draft.id,
            [drafting.AcceptedNarrative(key="narrative.organization_description", value="   ")],
            [], [],
            actor_id=None,
        )


def test_nothing_to_apply_is_refused(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    with pytest.raises(ValidationError):
        drafting.apply_draft(db, draft.id, [], [], [], actor_id=None)


def test_a_draft_cannot_be_applied_twice(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)
    accepted = [drafting.AcceptedNarrative(key="narrative.organization_description", value="x")]
    drafting.apply_draft(db, draft.id, accepted, [], [], actor_id=None)

    with pytest.raises(ConflictError):
        drafting.apply_draft(db, draft.id, accepted, [], [], actor_id=None)


def test_a_bad_value_is_refused_before_anything_is_written(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    with pytest.raises(ValidationError):
        drafting.apply_draft(
            db, draft.id,
            [drafting.AcceptedNarrative(key="narrative.organization_description", value="ok")],
            [drafting.AcceptedIssue(key="issue.0", category="", issue="")],
            [],
            actor_id=None,
        )

    db.refresh(draft)
    assert draft.status == DraftStatus.READY
    assert service.get_or_create(db).organization_description is None


def test_applying_withdraws_an_approval_the_same_as_editing_by_hand(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)
    service.submit_for_review(db, actor_id=None)
    service.approve(db, actor_id=None)

    drafting.apply_draft(
        db, draft.id,
        [drafting.AcceptedNarrative(key="narrative.organization_description", value="Edited.")],
        [], [],
        actor_id=None,
    )

    from app.models.organization_context import OrganizationContextStatus

    assert service.get_or_create(db).status == OrganizationContextStatus.DRAFT


def test_a_discarded_draft_cannot_then_be_applied(configured, model) -> None:
    db = configured
    draft = drafting.generate_draft(db, actor_id=None)

    drafting.discard_draft(db, draft.id, actor_id=None)

    assert drafting.latest_draft(db) is None
    with pytest.raises(ConflictError):
        drafting.apply_draft(
            db, draft.id,
            [drafting.AcceptedNarrative(key="narrative.organization_description", value="x")],
            [], [],
            actor_id=None,
        )


def test_applying_an_unknown_draft_id_is_not_found(configured, model) -> None:
    db = configured

    with pytest.raises(NotFoundError):
        drafting.apply_draft(db, 999_999, [], [], [], actor_id=None)


def test_two_people_applying_the_same_draft_at_once_cannot_both_succeed(configured, model) -> None:
    """The race the status check can't catch: both requests read the draft as
    ready before either writes. Only the conditional claim decides which
    wins -- see risk_item_suggestion_service's identical race test."""
    from sqlalchemy import update as sa_update

    db = configured
    draft = drafting.generate_draft(db, actor_id=None)
    accepted = [drafting.AcceptedNarrative(key="narrative.organization_description", value="x")]

    db.execute(
        sa_update(AiDraft)
        .where(AiDraft.id == draft.id)
        .values(status=DraftStatus.APPLIED)
        .execution_options(synchronize_session=False)
    )
    assert draft.status == DraftStatus.READY  # the stale read the race produces

    with patch.object(drafting, "_draft_for", return_value=draft):
        with pytest.raises(ConflictError):
            drafting.apply_draft(db, draft.id, accepted, [], [], actor_id=None)
    assert service.get_or_create(db).organization_description is None
