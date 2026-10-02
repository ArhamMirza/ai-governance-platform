from types import SimpleNamespace

import pytest

from app.core.eu_ai_act_scope import ARTICLE_RULES, automatic_applicability
from app.core.framework_reference_data import EU_AI_ACT_CONTROLS


def settings(**overrides) -> SimpleNamespace:
    defaults = dict(
        in_scope=True,
        scope_justification=None,
        is_provider=False,
        is_deployer=False,
        is_importer=False,
        is_distributor=False,
        has_high_risk_systems=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_every_tracked_article_has_a_rule() -> None:
    assert {code for code, _, _ in EU_AI_ACT_CONTROLS} == set(ARTICLE_RULES)


def test_everything_applies_until_assessed() -> None:
    assert automatic_applicability(None, "Art.16")[0] is True
    assert automatic_applicability(settings(in_scope=None), "Art.16")[0] is True


def test_nothing_applies_out_of_scope_and_the_justification_is_the_reason() -> None:
    applicable, reason = automatic_applicability(
        settings(in_scope=False, scope_justification="No EU customers or operations."),
        "Art.6",
    )

    assert applicable is False
    assert "No EU customers or operations." in reason


def test_a_deployer_is_not_held_to_provider_obligations() -> None:
    deployer = settings(is_deployer=True)

    applicable, reason = automatic_applicability(deployer, "Art.16")
    assert applicable is False
    assert "providers" in reason
    assert automatic_applicability(deployer, "Art.26")[0] is True


def test_a_provider_is_not_held_to_deployer_obligations() -> None:
    provider = settings(is_provider=True)

    assert automatic_applicability(provider, "Art.26")[0] is False
    assert automatic_applicability(provider, "Art.9")[0] is True


@pytest.mark.parametrize(
    ("role", "code"), [("is_importer", "Art.23"), ("is_distributor", "Art.24")]
)
def test_importer_and_distributor_articles_follow_their_role(role: str, code: str) -> None:
    assert automatic_applicability(settings(**{role: True}), code)[0] is True
    assert automatic_applicability(settings(is_provider=True), code)[0] is False


def test_holding_any_one_of_several_roles_is_enough() -> None:
    assert automatic_applicability(settings(is_distributor=True), "Art.25")[0] is True


def test_high_risk_only_articles_drop_out_without_high_risk_systems() -> None:
    provider = settings(is_provider=True, has_high_risk_systems=False)

    applicable, reason = automatic_applicability(provider, "Art.9")
    assert applicable is False
    assert "high-risk" in reason


def test_classification_applies_to_everyone_in_scope() -> None:
    nobody_high_risk = settings(is_deployer=True, has_high_risk_systems=False)

    assert automatic_applicability(nobody_high_risk, "Art.6")[0] is True
    assert automatic_applicability(nobody_high_risk, "Art.7")[0] is True


def test_an_article_without_a_rule_stays_applicable() -> None:
    assert automatic_applicability(settings(is_deployer=True), "Art.999")[0] is True
