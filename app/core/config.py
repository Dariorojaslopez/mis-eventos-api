from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Mis Eventos API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos",
        description="Async SQLAlchemy database URL",
    )
    database_echo: bool = False

    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = [
        "http://localhost:5173",
        "https://mis-eventos-web.vercel.app",
    ]

    log_level: str = "INFO"
    log_json: bool = True

    openai_api_key: str | None = Field(
        default=None,
        description="API key de OpenAI (opcional; mock funciona sin ella)",
    )
    ai_provider: Literal["mock", "openai"] = Field(
        default="mock",
        description="Proveedor IA: mock (sin red) u openai",
    )
    ai_openai_model: str = "gpt-4o-mini"
    ai_request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_max_retries: int = Field(default=2, ge=1, le=5)
    ai_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=10)
    ai_rate_limit_requests: int = Field(default=10, ge=1, le=1000)
    ai_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("database_url")
    @classmethod
    def validate_async_driver(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg:// driver")
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def run_db_migrations_on_startup(self) -> bool:
        return self.environment in {"production", "staging"}

    @property
    def sync_database_url(self) -> str:
        """URL síncrona para Alembic (psycopg no requerido: usamos asyncpg vía run_sync)."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
