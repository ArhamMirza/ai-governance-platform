"""Organization-wide context pinned into every grounded AI call.

Governance roles were already exercised indirectly through the drafting
services' tests; these test the shared module directly, plus the new
organization-context rendering and its caps.
"""

from sqlalchemy.orm import Session

from app.services import organization_context_service, pinned_context


def test_governance_roles_renders_every_role_with_responsibilities(db_session: Session) -> None:
    block = pinned_context.governance_roles(db_session)

    assert block is not None
    assert block["title"] == "Governance roles and responsibilities"
    assert block["href"] == "/governance"
    assert "Chief AI Governance Officer: Managing and approving." in block["text"]


def test_organization_context_is_none_when_nothing_is_set(db_session: Session) -> None:
    organization_context_service.get_or_create(db_session)

    assert pinned_context.organization_context(db_session) is None


def test_organization_context_renders_the_narrative(db_session: Session) -> None:
    organization_context_service.get_or_create(db_session)
    organization_context_service.update(
        db_session,
        {
            "organization_description": "A resume-screening company.",
            "ai_usage_overview": "Ranks job applicants.",
        },
        actor_id=None,
    )

    block = pinned_context.organization_context(db_session)

    assert block is not None
    assert block["title"] == "Context of the organization"
    assert block["href"] == "/organization-context"
    assert "A resume-screening company." in block["text"]
    assert "Ranks job applicants." in block["text"]


def test_organization_context_renders_issues_and_interested_parties(db_session: Session) -> None:
    organization_context_service.get_or_create(db_session)
    organization_context_service.add_issue(
        db_session,
        {"category": "External", "issue": "New regulation", "planned_response": "Track it."},
        actor_id=None,
    )
    organization_context_service.add_interested_party(
        db_session,
        {"party": "Regulators", "needs": "Evidence of compliance"},
        actor_id=None,
    )

    block = pinned_context.organization_context(db_session)

    assert block is not None
    assert "New regulation" in block["text"]
    assert "Track it." in block["text"]
    assert "Regulators" in block["text"]
    assert "Evidence of compliance" in block["text"]


def test_a_row_with_every_cell_blank_contributes_nothing(db_session: Session) -> None:
    """Category is the only thing filled in -- a row with no words in it
    shouldn't render as a bare, information-free bullet."""
    organization_context_service.get_or_create(db_session)
    organization_context_service.add_issue(db_session, {"category": "Internal"}, actor_id=None)

    block = pinned_context.organization_context(db_session)

    assert block is not None
    assert "Internal" in block["text"]


def test_rows_beyond_the_cap_are_summarised_not_dropped_silently(db_session: Session) -> None:
    organization_context_service.get_or_create(db_session)
    for i in range(pinned_context.MAX_ROWS + 5):
        organization_context_service.add_issue(
            db_session, {"category": "Internal", "issue": f"Issue {i}"}, actor_id=None
        )

    block = pinned_context.organization_context(db_session)

    assert block is not None
    assert block["text"].count("category: Internal") == pinned_context.MAX_ROWS
    assert "...and 5 more not shown." in block["text"]


def test_a_long_cell_is_truncated(db_session: Session) -> None:
    organization_context_service.get_or_create(db_session)
    organization_context_service.add_issue(
        db_session,
        {"category": "Internal", "issue": "x" * (pinned_context.MAX_CELL_CHARS + 200)},
        actor_id=None,
    )

    block = pinned_context.organization_context(db_session)

    assert block is not None
    assert "x" * pinned_context.MAX_CELL_CHARS in block["text"]
    assert "x" * (pinned_context.MAX_CELL_CHARS + 1) not in block["text"]


def test_organization_context_includes_the_scope_and_its_exclusions(db_session: Session) -> None:
    organization_context_service.update(
        db_session,
        {
            "aims_scope": "All production AI systems.",
            "aims_scope_exclusions": "Prototypes without customer data.",
        },
        actor_id=None,
    )

    source = pinned_context.organization_context(db_session)

    assert source is not None
    assert "Scope of the AI management system: All production AI systems." in source["text"]
    assert "Excluded from the scope: Prototypes without customer data." in source["text"]
