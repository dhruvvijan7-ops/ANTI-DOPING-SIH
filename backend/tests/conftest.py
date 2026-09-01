"""Pytest fixtures.

For integration/API tests we use a dedicated test schema on the same PostgreSQL
instance and create/drop it around each test session via Alembic.
"""
from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Force a test database BEFORE importing app modules so settings/engine point at it.
# Local dev Postgres is exposed on the host port 54320 (see .env POSTGRES_HOST_PORT);
# CI overrides TEST_DATABASE_URL to target its own service container on 5432.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://clean_sport:clean_sport@localhost:54320/clean_sport_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEPLOY_INITIAL_USERS"] = "true"

# Build a module-level engine bound to the test URL.
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    """Create schema fresh, then drop it after the session."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "migrations")
    # Alembic reads DATABASE_URL from settings via env.py
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    # Seed roles/users by running the seed against the test DB.
    from app.db.seed import run_seed

    with TestingSession() as db:
        run_seed(db)
    yield
    command.downgrade(alembic_cfg, "base")


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = TestingSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_client(client: TestClient) -> TestClient:
    return _authed_client(client, "admin", os.environ.get("INITIAL_ADMIN_PASSWORD", "ChangeMeAdmin123!"))


@pytest.fixture()
def investigator_client(client: TestClient) -> TestClient:
    return _authed_client(client, "investigator", "investigator-Passw0rd!")


@pytest.fixture()
def analyst_client(client: TestClient) -> TestClient:
    return _authed_client(client, "analyst", "analyst-Passw0rd!")


@pytest.fixture()
def viewer_client(client: TestClient) -> TestClient:
    return _authed_client(client, "viewer", "viewer-Passw0rd!")


def _authed_client(client: TestClient, username: str, password: str) -> TestClient:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"login failed for {username}: {resp.text}"
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
