"""Authentication service: login, logout, and session handling."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.identity import User
from app.schemas.auth import TokenResponse, UserResponse
from app.security.passwords import verify_password
from app.security.tokens import create_access_token


class InvalidCredentialsError(Exception):
    pass


def _to_user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def authenticate_and_issue_token(db: Session, username: str, password: str) -> TokenResponse:
    """Authenticate a user by username/password and issue an access token."""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    if not user.is_active or user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    now = datetime.now(timezone.utc)
    user.last_login_at = now
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_response(user),
    )


def get_current_user_response(db: Session, user_id: uuid.UUID) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_user_response(user)


def logout() -> None:
    """Revoke the current session.

    For stateless JWT access tokens, immediate server-side revocation is handled by
    the client dropping the token. A token denylist is intentionally not implemented
    in this stage to keep the stateless design; see DECISIONS.md for the documented
    tradeoff. The endpoint exists to support frontend logout flow and is audited.
    """
    return None
