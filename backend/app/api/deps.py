"""FastAPI dependencies for authentication and RBAC enforcement.

Authorization is always resolved server-side from the database using the role
attached to the authenticated user. The client cannot influence this.
"""
from __future__ import annotations

import uuid
from typing import Callable, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.identity import User
from app.security.rbac import Permissions
from app.security.tokens import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


class AuthenticationRequiredError(HTTPException):
    pass


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str | None = None,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token.

    Also verifies the user is active. Role/permissions are loaded from the DB.
    """
    if token is None:
        raise _credentials_exception()

    try:
        subject = decode_access_token(token)
    except TokenError:
        raise _credentials_exception()

    user = db.get(User, uuid.UUID(subject))
    if user is None:
        raise _credentials_exception()
    if not user.is_active or user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


def require_permissions(*permissions: str) -> Callable:
    """Dependency factory requiring ALL listed permissions on the current user."""

    def checker(user: User = Depends(get_current_user)) -> User:
        granted = {p.key for p in user.role.permissions}
        missing = [p for p in permissions if p not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission(s): {', '.join(missing)}",
            )
        return user

    return checker


def require_any_permission(permissions: List[str]) -> Callable:
    """Dependency factory requiring ANY of the listed permissions."""

    def checker(user: User = Depends(get_current_user)) -> User:
        granted = {p.key for p in user.role.permissions}
        if not any(p in granted for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return user

    return checker
