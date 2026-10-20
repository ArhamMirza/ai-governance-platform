import os
from functools import lru_cache

from pydantic import model_validator

# LiteLLM downloads its model price list from raw.githubusercontent.com the
# moment it is imported. No record data goes with it, but it is still an
# outbound connection -- on a deployment running a self-hosted model, the
# settings page tells people nothing leaves the building, and on an
# air-gapped network the import stalls until the fetch times out. The copy
# bundled with the package is used instead. Set here, at the earliest import
# in the app, because it only takes effect if it is set before LiteLLM loads.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
from pydantic_settings import BaseSettings, SettingsConfigDict

# The value shipped in .env.example. It is public, so anything encrypted
# under it is obfuscated rather than protected -- see the check below.
DEFAULT_SECRET_KEY = "change-me-in-a-real-deployment"

_REAL_DEPLOYMENTS = {"production", "prod", "staging", "test"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ai_governance.db"
    evidence_storage_dir: str = "./storage/evidence"
    secret_key: str = DEFAULT_SECRET_KEY
    cors_origins: str = "http://localhost:5173"
    # False for local http dev; set true once served over https.
    cookie_secure: bool = False
    # Anything other than "development" is treated as a real deployment and
    # held to the secret_key check below.
    environment: str = "development"
    # The code that guards creating the first account on a real deployment
    # (see app.core.setup_code). Left unset, the server makes one up at
    # startup and prints it in its log.
    setup_code: str | None = None

    @property
    def session_cookie_name(self) -> str:
        """The `__Host-` prefix makes the browser refuse the cookie unless it
        is Secure, has no Domain and covers the whole site, which also stops a
        sibling subdomain from planting one. It needs https, so it is used
        exactly when cookie_secure is."""
        return "__Host-session" if self.cookie_secure else "session_token"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_real_deployment(self) -> bool:
        return self.environment.strip().lower() in _REAL_DEPLOYMENTS

    @model_validator(mode="after")
    def _refuse_wildcard_origins(self) -> "Settings":
        """Credentialed requests must name the sites they trust. A wildcard
        here would let any website call the API as the signed-in user."""
        if any("*" in origin for origin in self.cors_origin_list):
            raise ValueError(
                "CORS_ORIGINS must list the exact origins to trust "
                "(e.g. https://governance.example.com), not a wildcard."
            )
        return self

    @model_validator(mode="after")
    def _refuse_the_example_secret(self) -> "Settings":
        """Refuse to start a real deployment on the published secret.

        secret_key derives the key that encrypts stored AI provider credentials
        and two-step sign-in secrets, and keys the signature on two-step
        sign-in tickets. Left at the example value, all of that is recoverable
        by anyone who can read this repository -- so this is an error at
        startup rather than a line in a README nobody reads.
        """
        if self.is_real_deployment and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is still the example value from .env.example. It encrypts stored "
                "AI provider keys and two-step sign-in secrets, so a real deployment needs its "
                "own. Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return self

    @model_validator(mode="after")
    def _require_secure_cookies_on_a_real_deployment(self) -> "Settings":
        """Refuse to start a real deployment with cookie_secure left False.

        Without the Secure flag, the browser will happily send the session
        cookie over a plain http connection -- exactly the case a public
        deployment (reachable outside a trusted local network) can't rule
        out. cookie_secure defaults to False only so a fresh checkout still
        runs over http://localhost without extra setup.
        """
        if self.is_real_deployment and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SECURE is False on a real deployment. Session cookies would be sent "
                "over plain http. Set COOKIE_SECURE=true (the deployment must be served over "
                "https for the cookie to still reach it)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
