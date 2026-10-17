"""Configuration, lue dans les variables d'environnement `JULIA_*` (ou le fichier `.env`)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SALT = "dev-salt"


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


class EngineMode(StrEnum):
    FAKE = "fake"
    POSTGRES = "postgres"


class RerankerMode(StrEnum):
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JULIA_", env_file=".env", extra="ignore")

    env: Environment = Environment.DEV
    engine: EngineMode = EngineMode.FAKE
    database_url: str | None = None
    data_raw_dir: Path = Path("data/raw")

    embedding_model: str = "BAAI/bge-m3"
    reranker: RerankerMode = RerankerMode.NONE
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    model_device: str | None = None

    retrieve_k: int = Field(default=30, ge=1, le=200)
    context_k: int = Field(default=8, ge=1, le=30)
    min_relevance: float = Field(default=0.45, ge=0.0, le=1.0)
    reference_year: int = 2026
    max_passage_chars: int = Field(default=6000, ge=500)
    embedding_max_tokens: int = Field(default=1024, ge=64, le=8192)

    llm_provider: Literal["openai_compatible", "extractive"] = "openai_compatible"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: SecretStr | None = None
    llm_model: str = "deepseek-flash"
    llm_extra_body: dict[str, Any] = Field(default_factory=lambda: {"thinking": {"type": "disabled"}})
    llm_timeout_s: float = 60.0
    llm_max_tokens: int = 1500
    llm_fallback_base_url: str | None = None
    llm_fallback_api_key: SecretStr | None = None
    llm_fallback_model: str | None = None
    llm_fallback_extra_body: dict[str, Any] = Field(default_factory=dict)

    rate_limit_client_per_minute: int = 6
    rate_limit_client_per_day: int = 60
    rate_limit_ip_per_minute: int = 120
    daily_answer_budget: int = 5000

    admin_token: SecretStr | None = None
    cors_origins: list[str] = Field(default_factory=list)
    trace_salt: SecretStr = SecretStr(_DEV_SALT)

    @model_validator(mode="after")
    def _check_consistency(self) -> Settings:
        if self.engine is EngineMode.POSTGRES and not self.database_url:
            raise ValueError("JULIA_DATABASE_URL est requis avec JULIA_ENGINE=postgres")
        if self.env is Environment.PROD:
            missing = [
                name
                for name, ok in (
                    ("JULIA_ENGINE=postgres", self.engine is EngineMode.POSTGRES),
                    ("JULIA_LLM_PROVIDER=openai_compatible", self.llm_provider == "openai_compatible"),
                    ("JULIA_LLM_API_KEY", self.llm_api_key is not None),
                    ("JULIA_ADMIN_TOKEN", self.admin_token is not None),
                    ("JULIA_TRACE_SALT", self.trace_salt.get_secret_value() != _DEV_SALT),
                )
                if not ok
            ]
            if missing:
                raise ValueError(f"configuration de production incomplète : {', '.join(missing)}")
        return self
