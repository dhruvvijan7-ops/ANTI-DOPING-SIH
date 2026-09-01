"""JWT token creation and validation.

Access tokens carry a stable user id and expiry. Roles/permissions are resolved
server-side from the database, never from client-visible claims (directive §36/§60).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


class TokenError(Exception):
    """Raised when a token is invalid, expired, or malformed."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject_id: uuid.UUID) -> str:
    """Create a signed JWT access token for the given user id."""
    now = _now()
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject_id),
        "iat": now,
        "exp": expires,
        "nbf": now,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_token_audience,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> str:
    """Validate a token and return the subject (user id) as a string.

    Raises TokenError on any validation failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_token_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:  # includes ExpiredSignatureError, etc.
        raise TokenError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise TokenError("Unexpected token type")

    subject = payload.get("sub")
    if not subject:
        raise TokenError("Token missing subject")
    return subject
