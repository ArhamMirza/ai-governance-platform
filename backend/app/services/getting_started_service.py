"""What a new installation still needs, worked out from the records.

Nothing here is stored: a step is done when the records it asks for exist, so the
list can never disagree with the platform, and a step someone undoes (deleting the
last policy, say) shows up as to-do again. The order is the one a person should
take, and it is the answer to "what do I fill in first": the organization and its
roles come first because the AI roles chosen there carry through to the AI systems
and to the EU AI Act assessment, and the records that the assessments draw on
(systems, policies, tools, suppliers) come before the assessments themselves.
"""

from sqlalchemy.orm import Session

from app.models.policy import PolicyStatus
from app.models.supplier import SupplierStatus
from app.repositories import governance_role_repository, user_repository
from app.schemas.dashboard import GettingStarted, GettingStartedStep
from app.services import (
    ai_assist_service,
    ai_system_inventory_service,
    ai_tool_service,
    eu_ai_act_service,
    governance_role_service,
    impact_assessment_service,
    organization_context_service,
    policy_service,
    supplier_service,
)


def _organization_described(db: Session) -> bool:
    context = organization_context_service.get_or_create(db)
    return bool((context.organization_description or "").strip())


def _caigo_assigned(db: Session) -> bool:
    role = governance_role_repository.get_by_name(
        db, governance_role_service.CHIEF_AI_GOVERNANCE_OFFICER
    )
    return role is not None and governance_role_repository.count_holders(db, role.id) > 0


def _more_than_one_person(db: Session) -> bool:
    return sum(1 for user in user_repository.list_all(db) if user.is_active) > 1


def _eu_ai_act_assessed(db: Session) -> bool:
    settings = eu_ai_act_service.get_settings(db)
    return settings is not None and settings.in_scope is not None


def get(db: Session) -> GettingStarted:
    def step(key, title, why, href, done, optional=False) -> GettingStartedStep:
        return GettingStartedStep(
            key=key, title=title, why=why, href=href, done=bool(done), optional=optional
        )

    steps = [
        step(
            "organization",
            "Describe your organization",
            "Start here. The AI roles you choose carry through to your AI systems and to "
            "the EU AI Act assessment.",
            "/organization-context",
            _organization_described(db),
        ),
        step(
            "roles",
            "Assign the Chief AI Governance Officer",
            "They approve policies and AI tools. Until someone holds the role, nothing "
            "waiting on approval can be finished.",
            "/governance",
            _caigo_assigned(db),
        ),
        step(
            "people",
            "Add the people who will use it",
            "Import a CSV or add people one at a time. Staff who only need to ask for AI "
            "tools get a login that reaches just their own pages.",
            "/users",
            _more_than_one_person(db),
        ),
        step(
            "ai_systems",
            "Record your AI systems",
            "The inventory of what you build or use. Impact assessments, risks and the "
            "dashboard all hang off it.",
            "/ai-systems",
            ai_system_inventory_service.list_rows(db),
        ),
        step(
            "eu_scope",
            "Assess whether the EU AI Act applies",
            "Decides which of its articles count toward your coverage, so the numbers "
            "reflect your real obligations.",
            "/frameworks",
            _eu_ai_act_assessed(db),
        ),
        step(
            "policies",
            "Write your AI policy",
            "Draft it, then have it approved. It is the anchor most other controls point at.",
            "/policies",
            any(p.status != PolicyStatus.RETIRED for p in policy_service.list_policies(db)),
        ),
        step(
            "tools",
            "Decide which AI tools staff may use",
            "Approve the tools people already use and say what data each may be given.",
            "/ai-tools",
            ai_tool_service.approved_tools(db),
        ),
        step(
            "suppliers",
            "Record the suppliers behind your AI",
            "The vendors and model providers you depend on, with how often to review them.",
            "/suppliers",
            any(
                s.status == SupplierStatus.ACTIVE for s in supplier_service.list_suppliers(db)
            ),
        ),
        step(
            "assessment",
            "Complete a first impact assessment",
            "Open an AI system and start its impact assessment: the first real piece of "
            "evidence your coverage will count.",
            "/ai-systems",
            impact_assessment_service.list_all(db),
        ),
        step(
            "assistant",
            "Turn on AI assistance",
            "Optional. Drafts and a search over your records, with checked citations. Works "
            "with a model you host yourself as well as the hosted ones.",
            "/settings",
            ai_assist_service.status(db).available,
            optional=True,
        ),
    ]

    required = [s for s in steps if not s.optional]
    return GettingStarted(
        steps=steps,
        done_count=sum(1 for s in steps if s.done),
        total=len(steps),
        complete=all(s.done for s in required),
        next_key=next((s.key for s in required if not s.done), None),
    )
