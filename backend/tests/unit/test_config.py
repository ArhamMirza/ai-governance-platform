"""Deployment settings, and the one that must not be left at its example.

secret_key signs session cookies and derives the key that encrypts stored AI
provider credentials. The value in .env.example is published in this
repository, so a deployment running on it is not encrypting anything from
anyone who has read the source.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings


@pytest.mark.parametrize("environment", ["production", "PROD", "staging", "test"])
def test_a_real_deployment_refuses_to_start_on_the_example_secret(environment: str) -> None:
    with pytest.raises(PydanticValidationError) as caught:
        Settings(environment=environment, secret_key=DEFAULT_SECRET_KEY)

    # The message has to say what to do about it, not just that it's wrong.
    assert "SECRET_KEY" in str(caught.value)
    assert "token_urlsafe" in str(caught.value)


def test_local_development_still_runs_on_the_example_secret() -> None:
    """Refusing here would make a fresh checkout fail to start, which is a
    worse first experience than the risk it would avert on a laptop."""
    settings = Settings(environment="development", secret_key=DEFAULT_SECRET_KEY)

    assert settings.secret_key == DEFAULT_SECRET_KEY
    assert settings.is_real_deployment is False


def test_a_real_deployment_starts_once_the_secret_is_its_own() -> None:
    settings = Settings(environment="production", secret_key="a-secret-of-its-own")

    assert settings.is_real_deployment is True
