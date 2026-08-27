from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ai_governance.db"
    evidence_storage_dir: str = "./storage/evidence"
    secret_key: str = "change-me-in-a-real-deployment"
    cors_origins: str = "http://localhost:5173"
    # False for local http dev; set true once served over https.
    cookie_secure: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
