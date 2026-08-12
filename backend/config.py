"""POLIS configuration — Implementation Plan task 1.6.

THE ONLY MODULE THAT READS THE ENVIRONMENT. Everything else imports
`get_settings()`. Scattering `os.getenv` calls through the codebase is how a
secret ends up in a log line or a frontend bundle (SEC-17).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # tolerate unrelated vars in the ambient environment
        # MODEL_* env vars are ML settings, not pydantic model internals.
        protected_namespaces=(),
    )

    # ---- Application ----
    polis_env: Literal["local", "test", "demo", "production"] = "local"
    polis_debug: bool = False
    polis_log_level: str = "INFO"

    # ---- Database ----
    database_url: SecretStr = SecretStr("postgresql+psycopg://polis_app:@localhost:5432/polis")

    # ---- Security ----
    jwt_secret: SecretStr = SecretStr("")
    jwt_issuer: str = "polis"
    jwt_audience: str = "polis-api"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_hours: int = Field(default=8, ge=1, le=24)
    cors_allowed_origins: str = "http://localhost:5173"

    # ---- Ingestion ----
    ingest_user_agent: str = "POLIS-Academic-Research/1.0 (university FYP)"
    ingest_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    ingest_max_bytes: int = Field(default=2_097_152, gt=0)
    # Derived from the PRD §11.1 latency budget — see the validator below.
    ingest_interval_minutes: int = Field(default=10, ge=1, le=1440)

    # ---- Source credentials ----
    telegram_api_id: str = ""
    telegram_api_hash: SecretStr = SecretStr("")
    telegram_session_name: str = "polis"
    reddit_client_id: str = ""
    reddit_client_secret: SecretStr = SecretStr("")
    reddit_user_agent: str = ""

    # ---- ML ----
    model_artifact_uri: str = ""
    model_device: str = "cpu"
    model_max_tokens: int = Field(default=512, gt=0)
    model_batch_size: int = Field(default=8, gt=0)
    model_scoring_batch_limit: int = Field(default=100, gt=0)
    model_confidence_floor: float = Field(default=0.55, ge=0.0, le=1.0)

    # ---- Retention (PRIV-4) ----
    retain_raw_content_days: int = Field(default=180, gt=0)
    retain_nlp_results_days: int = Field(default=365, gt=0)
    retain_audit_days: int = Field(default=365, gt=0)

    @property
    def cors_origins(self) -> list[str]:
        """Explicit allowlist. Never a wildcard when credentials are allowed (SEC-15)."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_local(self) -> bool:
        return self.polis_env == "local"

    @field_validator("ingest_interval_minutes")
    @classmethod
    def _interval_within_latency_budget(cls, v: int) -> int:
        """PRD §11.1: poll wait is stage A of the 20-minute budget.

        Above 10 minutes the worst case exceeds NFR-1.5a. This is a derived
        value, not a free knob — fail loudly rather than silently miss the NFR.
        """
        if v > 10:
            raise ValueError(
                f"INGEST_INTERVAL_MINUTES={v} exceeds the PRD §11.1 latency budget "
                "(stage A must be <= 10 min or NFR-1.5a is unmet)"
            )
        return v

    def assert_production_safe(self) -> None:
        """Fail fast on a misconfigured non-local deployment.

        Called at app startup. A missing JWT secret or debug-mode-on in demo is a
        security defect that must stop the process, not warn into a log nobody reads.
        """
        if self.is_local:
            return
        problems: list[str] = []
        if self.polis_debug:
            problems.append("POLIS_DEBUG must be false outside local (SEC-19)")
        if len(self.jwt_secret.get_secret_value()) < 32:
            problems.append("JWT_SECRET must be at least 32 characters (SEC-5)")
        if "*" in self.cors_allowed_origins:
            problems.append("CORS_ALLOWED_ORIGINS must not contain a wildcard (SEC-15)")
        if problems:
            raise RuntimeError("Unsafe configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
