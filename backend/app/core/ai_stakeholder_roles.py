"""The AI stakeholder roles an organization can hold -- the vocabulary
ISO/IEC 42001 clause 4.1 draws on from ISO/IEC 22989 (AI provider, AI
producer, AI customer, AI partner), with their sub-roles.

Recorded as the organization's own statement of what it does, organization-
wide and optionally per AI system. Only a hint toward the EU AI Act roles
is derived from them (suggested_eu_roles); nothing is decided by them.

The standard's other stakeholder groups, AI subjects and relevant
authorities, are about who the organization affects or answers to rather
than roles it holds, so they're not here -- see the interested-parties
sheet and the impact assessment.
"""

from dataclasses import dataclass

from app.core.eu_ai_act_scope import EuAiActRole


@dataclass(frozen=True)
class AIRole:
    code: str
    label: str
    parent: str  # The main role this sub-role belongs to.
    description: str


PROVIDER = "AI provider"
PRODUCER = "AI producer"
CUSTOMER = "AI customer"
PARTNER = "AI partner"

AI_ROLES: list[AIRole] = [
    AIRole(
        "platform_provider",
        "AI platform provider",
        PROVIDER,
        "Offers an AI platform that others build or run AI systems on.",
    ),
    AIRole(
        "product_or_service_provider",
        "AI product or service provider",
        PROVIDER,
        "Offers an AI product or service to customers.",
    ),
    AIRole(
        "developer",
        "AI developer",
        PRODUCER,
        "Builds and trains AI systems or models.",
    ),
    AIRole(
        "designer",
        "AI designer",
        PRODUCER,
        "Defines what an AI system is for and how it should behave.",
    ),
    AIRole(
        "integrator",
        "AI integrator",
        PRODUCER,
        "Combines AI components into a working AI system.",
    ),
    AIRole(
        "ai_user",
        "AI user",
        CUSTOMER,
        "Uses an AI system, or a service built on one, within the organization.",
    ),
    AIRole(
        "system_integrator",
        "AI system integrator",
        PARTNER,
        "Works with others to fit AI systems into their environments.",
    ),
    AIRole(
        "data_provider",
        "Data provider",
        PARTNER,
        "Supplies data used to train, test or run AI systems.",
    ),
    AIRole(
        "ai_evaluator",
        "AI evaluator",
        PARTNER,
        "Tests or assesses AI systems against requirements.",
    ),
    AIRole(
        "ai_auditor",
        "AI auditor",
        PARTNER,
        "Audits AI systems or the management system around them.",
    ),
]

ROLE_CODES = frozenset(role.code for role in AI_ROLES)

# The EU AI Act role each AI role most plausibly points to. Partners have no
# counterpart: an evaluator or data provider isn't one of the Act's roles.
_SUGGESTED_EU_ROLE: dict[str, EuAiActRole] = {
    **{role.code: EuAiActRole.PROVIDER for role in AI_ROLES if role.parent in (PROVIDER, PRODUCER)},
    "ai_user": EuAiActRole.DEPLOYER,
}


def unknown_codes(codes: list[str]) -> list[str]:
    return [code for code in codes if code not in ROLE_CODES]


def suggested_eu_roles(codes: list[str]) -> set[EuAiActRole]:
    """The EU AI Act roles these AI roles point to -- a hint for the person
    filling in the applicability assessment, never a decision."""
    return {_SUGGESTED_EU_ROLE[code] for code in codes if code in _SUGGESTED_EU_ROLE}
