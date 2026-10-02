"""Which EU AI Act articles apply to an organization.

Whether the Act applies at all depends on territorial scope (Art. 2); which
of its obligations apply depends on the organization's role in the value
chain and on whether it provides or deploys high-risk AI systems -- most of
Chapter III only bites for high-risk systems.

This applies the organization's own recorded assessment (see
EuAiActApplicability) consistently across the articles the platform tracks.
It doesn't decide scope or classification; those are the organization's
calls, recorded with a justification. A per-article override (a
FrameworkSoaEntry row) can always correct the automatic answer.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class EuAiActRole(StrEnum):
    PROVIDER = "provider"
    DEPLOYER = "deployer"
    IMPORTER = "importer"
    DISTRIBUTOR = "distributor"


ROLE_NAMES = {
    EuAiActRole.PROVIDER: "providers",
    EuAiActRole.DEPLOYER: "deployers",
    EuAiActRole.IMPORTER: "importers",
    EuAiActRole.DISTRIBUTOR: "distributors",
}


@dataclass(frozen=True)
class ArticleRule:
    # None = applies whatever the organization's role.
    roles: frozenset[EuAiActRole] | None
    high_risk_only: bool


_PROVIDER = frozenset({EuAiActRole.PROVIDER})
_HIGH_RISK_PROVIDER = ArticleRule(_PROVIDER, high_risk_only=True)

ARTICLE_RULES: dict[str, ArticleRule] = {
    # Classification applies to everyone in scope: it's how an organization
    # finds out whether it has high-risk systems at all.
    "Art.6": ArticleRule(None, high_risk_only=False),
    "Art.7": ArticleRule(None, high_risk_only=False),
    # Requirements for high-risk systems and the obligations of their
    # providers.
    **{f"Art.{n}": _HIGH_RISK_PROVIDER for n in range(8, 23)},
    "Art.23": ArticleRule(frozenset({EuAiActRole.IMPORTER}), high_risk_only=True),
    "Art.24": ArticleRule(frozenset({EuAiActRole.DISTRIBUTOR}), high_risk_only=True),
    # When someone other than the provider becomes one.
    "Art.25": ArticleRule(
        frozenset({EuAiActRole.IMPORTER, EuAiActRole.DISTRIBUTOR, EuAiActRole.DEPLOYER}),
        high_risk_only=True,
    ),
    "Art.26": ArticleRule(frozenset({EuAiActRole.DEPLOYER}), high_risk_only=True),
    "Art.27": ArticleRule(frozenset({EuAiActRole.DEPLOYER}), high_risk_only=True),
    "Art.72": _HIGH_RISK_PROVIDER,
    # Deployers report serious incidents too, but under Art. 26(5).
    "Art.73": _HIGH_RISK_PROVIDER,
}


class ApplicabilitySettings(Protocol):
    in_scope: bool | None
    scope_justification: str | None
    is_provider: bool
    is_deployer: bool
    is_importer: bool
    is_distributor: bool
    has_high_risk_systems: bool | None


def roles_of(settings: ApplicabilitySettings) -> set[EuAiActRole]:
    flags = {
        EuAiActRole.PROVIDER: settings.is_provider,
        EuAiActRole.DEPLOYER: settings.is_deployer,
        EuAiActRole.IMPORTER: settings.is_importer,
        EuAiActRole.DISTRIBUTOR: settings.is_distributor,
    }
    return {role for role, held in flags.items() if held}


def _role_list(roles: frozenset[EuAiActRole]) -> str:
    names = [ROLE_NAMES[role] for role in EuAiActRole if role in roles]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def automatic_applicability(settings: ApplicabilitySettings | None, code: str) -> tuple[bool, str]:
    """(applicable, reason) for one article, before any per-article
    override. Until the organization has assessed its applicability,
    everything applies -- the safe default, and the platform's behavior
    before this setting existed."""
    if settings is None or settings.in_scope is None:
        return True, "EU AI Act applicability not yet assessed."
    if settings.in_scope is False:
        justification = (settings.scope_justification or "").strip()
        reason = "Organization is outside the EU AI Act's scope"
        return False, f"{reason}: {justification}" if justification else f"{reason}."

    rule = ARTICLE_RULES.get(code)
    if rule is None:
        # An article with no rule stays in -- never silently drop one.
        return True, "Applies to organizations in scope."
    if rule.roles is not None and not (rule.roles & roles_of(settings)):
        role_list = _role_list(rule.roles)
        return False, f"Applies to {role_list}; your organization isn't recorded as one."
    if rule.high_risk_only and not settings.has_high_risk_systems:
        return False, (
            "Only applies to high-risk AI systems, and your organization doesn't "
            "provide or deploy any."
        )
    return True, "Applies to your organization's recorded role(s)."
