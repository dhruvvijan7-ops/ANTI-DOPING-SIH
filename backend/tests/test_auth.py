"""Authentication unit + integration tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.security.passwords import hash_password, verify_password


def test_password_hash_and_verify() -> None:
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_salted() -> None:
    a = hash_password("same")
    b = hash_password("same")
    assert a != b


def test_login_success(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "viewer-Passw0rd!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "viewer"
    assert body["user"]["role"]["name"] == "VIEWER"


def test_login_invalid_credentials(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_me_returns_user(client: TestClient, viewer_client: TestClient) -> None:
    resp = viewer_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "viewer"


def test_logout(client: TestClient, investigator_client: TestClient) -> None:
    resp = investigator_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
