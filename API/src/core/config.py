from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    app_env: AppEnv = AppEnv.DEVELOPMENT
    api_key: str = ""                    # Required in production — checked against X-Api-Key header
    gemini_api_key: str = ""
    unpaywall_email: str = "app@yourdomain.com"
    firebase_service_account_path: str = "./service-account.json"
    firebase_storage_bucket: str = ""
    # Stored as a comma-separated string so bare .env values like
    # CORS_ORIGINS=http://localhost:5173 work without JSON brackets.
    cors_origins_raw: str = "http://localhost:5173"
    agent_base_url: str = "http://localhost:8000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnv.DEVELOPMENT

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
