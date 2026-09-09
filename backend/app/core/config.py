"""Application configuration.

All secrets and environment-specific settings are read from environment
variables, never hardcoded. See `.env.example` at the repository root.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "VERITY — Anti-Doping Intelligence & Investigations Platform"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://clean_sport:clean_sport@localhost:5432/clean_sport",
        alias="DATABASE_URL",
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # Security
    jwt_secret_key: str = Field(default="change-me-dev-only", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_issuer: str = Field(default="clean-sport-api", alias="JWT_ISSUER")
    reset_token_expire_minutes: int = Field(
        default=30, alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES"
    )

    # Seed
    deploy_initial_users: bool = Field(default=True, alias="DEPLOY_INITIAL_USERS")
    initial_admin_password: str = Field(
        default="ChangeMeAdmin123!", alias="INITIAL_ADMIN_PASSWORD"
    )

    # AI decision support (STAGE H). When unset the deterministic fallback is used
    # so the UI continues to function without an external model provider.
    ai_provider: str = Field(default="", alias="LLM_PROVIDER")
    ai_api_key: str = Field(default="", alias="LLM_API_KEY")
    ai_model: str = Field(default="", alias="LLM_MODEL")
    ai_base_url: str = Field(default="", alias="LLM_BASE_URL")

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key and self.ai_base_url and self.ai_model)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    _DEV_ONLY_SECRETS = frozenset({"change-me-dev-only", "change_me", ""})

    def validate_production(self) -> None:
        """Fail fast when production settings still use known dev defaults.

        Must be called at application startup (see app.main.create_app) so a
        misconfigured deployment refuses to boot instead of serving traffic
        with placeholder credentials.
        """
        if not self.is_production:
            return
        if self.jwt_secret_key in self._DEV_ONLY_SECRETS or len(self.jwt_secret_key) < 32:
            raise RuntimeError(
                "Refusing to start in production: JWT_SECRET_KEY is missing or uses a known "
                "development default. Generate a strong secret (>= 32 chars) and set "
                "JWT_SECRET_KEY before starting."
            )
        if self.initial_admin_password == "ChangeMeAdmin123!":
            raise RuntimeError(
                "Refusing to start in production: INITIAL_ADMIN_PASSWORD still uses the "
                "documented default value. Set a unique strong password before starting."
            )

    @property
    def jwt_token_audience(self) -> str:
        return "clean-sport-frontend"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
