import pytest

from app.core import ai_stakeholder_roles as roles
from app.core.eu_ai_act_scope import EuAiActRole


def test_every_role_has_a_unique_code_and_a_known_main_role() -> None:
    codes = [role.code for role in roles.AI_ROLES]

    assert len(codes) == len(set(codes))
    assert {role.parent for role in roles.AI_ROLES} == {
        roles.PROVIDER,
        roles.PRODUCER,
        roles.CUSTOMER,
        roles.PARTNER,
    }


def test_unknown_codes_are_reported() -> None:
    assert roles.unknown_codes(["developer", "wizard", "ai_user", "oracle"]) == ["wizard", "oracle"]
    assert roles.unknown_codes([]) == []


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        (["platform_provider"], {EuAiActRole.PROVIDER}),
        (["product_or_service_provider"], {EuAiActRole.PROVIDER}),
        (["developer"], {EuAiActRole.PROVIDER}),
        (["designer"], {EuAiActRole.PROVIDER}),
        (["integrator"], {EuAiActRole.PROVIDER}),
        (["ai_user"], {EuAiActRole.DEPLOYER}),
        (["developer", "ai_user"], {EuAiActRole.PROVIDER, EuAiActRole.DEPLOYER}),
        # Partners aren't roles under the Act, so they point to nothing.
        (["system_integrator", "data_provider", "ai_evaluator", "ai_auditor"], set()),
        ([], set()),
        (["not_a_role"], set()),
    ],
)
def test_suggested_eu_roles(codes: list[str], expected: set[EuAiActRole]) -> None:
    assert roles.suggested_eu_roles(codes) == expected
