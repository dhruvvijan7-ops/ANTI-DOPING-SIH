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
    app_name: str = "CleanSport Intelligence API"
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

    # Seed
    deploy_initial_users: bool = Field(default=True, alias="DEPLOY_INITIAL_USERS")
    initial_admin_password: str = Field(
        default="ChangeMeAdmin123!", alias="INITIAL_ADMIN_PASSWORD"
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def jwt_token_audience(self) -> str:
        return "clean-sport-frontend"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
