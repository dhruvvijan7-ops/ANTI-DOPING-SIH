"""Authentication endpoints: login, logout, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.identity import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    MessageResponse,
    TokenResponse,
)
from app.security.rbac import Permissions
from app.services import audit_service, auth_service

logger = get_logger("clean_sport.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and issue an access token."""
    try:
        result = auth_service.authenticate_and_issue_token(
            db, payload.username, payload.password
        )
    except auth_service.InvalidCredentialsError:
        audit_service.record_audit(
            db,
            actor_id=None,
            action="auth.login.failed",
            entity_type="user",
            entity_id=payload.username,
            metadata={"reason": "invalid_credentials"},
            request_id=request.state.request_id,
        )
        db.commit()
        logger.info("Failed login attempt for %s", payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    audit_service.record_audit(
        db,
        actor_id=result.user.id,
        action="auth.login",
        entity_type="user",
        entity_id=str(result.user.id),
        request_id=request.state.request_id,
    )
    db.commit()
    return result


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, db: Session = Depends(get_db)) -> MessageResponse:
    """Invalidate the client session (client discards the token)."""
    auth_service.logout()
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    """Return the current authenticated user and their role/permissions."""
    return MeResponse.model_validate(user)
