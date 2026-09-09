"""Authentication unit + integration tests."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from app.core.config import settings
from app.models.identity import PasswordResetToken, User
from app.security.passwords import hash_password, verify_password


def _sign(payload: dict, *, in_future: bool = True) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5) if in_future else now - timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_token_audience,
        "type": "access",
        **payload,
    }
    return jose_jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


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


def test_garbage_token_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


def test_expired_token_rejected(client: TestClient) -> None:
    token = _sign({"sub": "00000000-0000-0000-0000-000000000001"}, in_future=False)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_non_uuid_subject_rejected(client: TestClient) -> None:
    token = _sign({"sub": "not-a-uuid"})
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_wrong_audience_rejected(client: TestClient) -> None:
    token = _sign({"sub": "00000000-0000-0000-0000-000000000001", "aud": "other-app"})
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_me_returns_user(client: TestClient, viewer_client: TestClient) -> None:
    resp = viewer_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "viewer"


def test_logout(client: TestClient, investigator_client: TestClient) -> None:
    resp = investigator_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


# --- Registration -----------------------------------------------------------

def test_register_creates_viewer_and_signs_in(client: TestClient) -> None:
    username = _unique_username("newviewer")
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "full_name": "New Viewer",
            "password": "NewPassw0rd!",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == username
    assert body["user"]["role"]["name"] == "VIEWER"
    # The new account can immediately use the token.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == username


def test_register_with_email(client: TestClient, db) -> None:
    username = _unique_username("withmail")
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.org",
            "password": "NewPassw0rd!",
        },
    )
    assert resp.status_code == 201
    user = db.query(User).filter_by(username=username).first()
    assert user is not None
    assert user.email == f"{username}@example.org"


def test_register_duplicate_username(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "viewer", "password": "NewPassw0rd!"},
    )
    assert resp.status_code == 409


def test_register_duplicate_email(client: TestClient) -> None:
    username = _unique_username("emaildup")
    email = f"{username}@example.org"
    first = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "NewPassw0rd!"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/auth/register",
        json={"username": _unique_username("emaildup2"), "email": email, "password": "NewPassw0rd!"},
    )
    assert second.status_code == 409


def test_register_weak_password_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": _unique_username("weak"), "password": "short"},
    )
    assert resp.status_code == 422


def test_register_invalid_username_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "has space", "password": "NewPassw0rd!"},
    )
    assert resp.status_code == 422


# --- Password reset ---------------------------------------------------------

def test_forgot_password_known_user_returns_dev_token(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "viewer"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "If an account exists" in body["message"]
    assert body["dev_reset_token"]


def test_forgot_password_unknown_identifier_is_neutral(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "no-such-person"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "If an account exists" in body["message"]
    assert body["dev_reset_token"] is None


def test_forgot_password_by_email(client: TestClient) -> None:
    username = _unique_username("bymail")
    email = f"{username}@example.org"
    registered = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "OldPassw0rd!"},
    )
    assert registered.status_code == 201
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": email},
    )
    assert resp.status_code == 200
    assert resp.json()["dev_reset_token"]


def test_forgot_password_production_never_returns_token(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "viewer"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dev_reset_token"] is None
    assert "If an account exists" in body["message"]


def test_reset_password_full_flow(client: TestClient) -> None:
    username = _unique_username("resetme")
    new_password = "FreshPassw0rd!"
    registered = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "OldPassw0rd!"},
    )
    assert registered.status_code == 201

    forgot = client.post("/api/v1/auth/forgot-password", json={"identifier": username})
    assert forgot.status_code == 200
    token = forgot.json()["dev_reset_token"]
    assert token

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "OldPassw0rd!"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": new_password},
    )
    assert new_login.status_code == 200


def test_reset_token_is_single_use(client: TestClient) -> None:
    username = _unique_username("singleuse")
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "OldPassw0rd!"},
    )
    token = client.post("/api/v1/auth/forgot-password", json={"identifier": username}).json()[
        "dev_reset_token"
    ]
    assert client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassw0rd!"},
    ).status_code == 200
    again = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPassw0rd!"},
    )
    assert again.status_code == 400


def test_reset_password_invalid_token(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewPassw0rd!"},
    )
    assert resp.status_code == 400
    assert "Invalid or expired reset token" in resp.json()["error"]["message"]


def test_reset_password_expired_token(client: TestClient, db) -> None:
    username = _unique_username("expired")
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "OldPassw0rd!"},
    )
    token = client.post("/api/v1/auth/forgot-password", json={"identifier": username}).json()[
        "dev_reset_token"
    ]
    record = (
        db.query(PasswordResetToken)
        .filter_by(token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest())
        .one()
    )
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassw0rd!"},
    )
    assert resp.status_code == 400


def test_reset_password_updates_hash(client: TestClient, db) -> None:
    username = _unique_username("hashcheck")
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "OldPassw0rd!"},
    )
    token = client.post("/api/v1/auth/forgot-password", json={"identifier": username}).json()[
        "dev_reset_token"
    ]
    client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassw0rd!"})
    user = db.query(User).filter_by(username=username).first()
    assert user is not None
    assert verify_password("NewPassw0rd!", user.password_hash)
    assert not verify_password("OldPassw0rd!", user.password_hash)


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
