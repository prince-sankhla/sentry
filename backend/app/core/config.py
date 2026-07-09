from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SENTRY API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sentry"

    # Optional multi-provider AI reasoning layer. Providers are tried in
    # ``llm_provider_order`` and the first configured one that answers wins; when
    # none is configured the investigation engine falls back to the deterministic
    # reasoning composer, so the platform is fully functional without any LLM.
    #
    # The model only ever *phrases* conclusions already proven by the backend
    # from the InvestigationPackage — it is never given authority to invent facts.
    llm_provider_order: str = "anthropic,openrouter,openai,gemini"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 30.0

    # Anthropic (official SDK)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"
    # Optional Anthropic-compatible endpoint (e.g. a proxy/gateway). When unset the
    # SDK uses the official api.anthropic.com base URL.
    anthropic_base_url: str | None = None

    # OpenRouter (OpenAI-compatible REST)
    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # OpenAI (OpenAI-compatible REST)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # Google Gemini (Generative Language REST)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
