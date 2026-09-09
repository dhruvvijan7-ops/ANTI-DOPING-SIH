"""Authentication service: registration, login, logout, password reset."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.identity import PasswordResetToken, Role, User
from app.schemas.auth import TokenResponse, UserResponse
from app.security.passwords import hash_password, verify_password
from app.security.rbac import Roles
from app.security.tokens import create_access_token


class InvalidCredentialsError(Exception):
    pass


class InvalidResetTokenError(Exception):
    """Raised when a reset token is invalid, expired, or already used."""


def _to_user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _issue_token(user: User) -> TokenResponse:
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_response(user),
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_user(
    db: Session,
    *,
    username: str,
    email: str | None,
    full_name: str | None,
    password: str,
) -> TokenResponse:
    """Create a least-privilege (VIEWER) account and sign the user in.

    Self-service registration is constrained to the VIEWER role; a role change
    to INVESTIGATOR/ANALYST is an administrative action.
    """
    role = db.scalar(select(Role).where(Role.name == Roles.VIEWER))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Base role misconfiguration: VIEWER role is not seeded",
        )

    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already registered")

    if email:
        email_owner = db.scalar(select(User).where(User.email == email))
        if email_owner is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


def create_password_reset_token(db: Session, user: User) -> str:
    """Create a one-time reset token and return the plaintext value.

    Only the SHA-256 digest is persisted. Any previously unused tokens for the
    user are invalidated so exactly one reset is outstanding at a time.
    """
    now = datetime.now(timezone.utc)
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    token = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=now + timedelta(minutes=settings.reset_token_expire_minutes),
    )
    db.add(record)
    db.commit()
    return token


def reset_password_with_token(
    db: Session,
    token: str,
    new_password: str,
) -> User:
    """Consume a reset token and replace the user's password (one-shot).

    Raises InvalidResetTokenError for unknown, expired, or already-used tokens so
    the caller can respond identically without revealing account details.
    """
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_token(token)
        )
    )
    if record is None or record.used_at is not None:
        raise InvalidResetTokenError()

    if record.expires_at <= datetime.now(timezone.utc):
        raise InvalidResetTokenError()

    record.used_at = datetime.now(timezone.utc)
    user = db.get(User, record.user_id)
    if user is None:
        raise InvalidResetTokenError()

    user.password_hash = hash_password(new_password)
    # Flush the used_at change first so the bulk DELETE of remaining unused
    # tokens cannot remove the token we are consuming this request.
    db.flush()
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    db.commit()
    db.refresh(user)
    return user


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

    return _issue_token(user)


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
