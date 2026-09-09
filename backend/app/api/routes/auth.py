"""Authentication endpoints: register, login, logout, current user, password reset."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.identity import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.security.rbac import Permissions
from app.services import audit_service, auth_service

logger = get_logger("clean_sport.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Create a least-privilege (VIEWER) account and sign the user in."""
    result = auth_service.register_user(
        db,
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    audit_service.record_audit(
        db,
        actor_id=result.user.id,
        action="auth.register",
        entity_type="user",
        entity_id=str(result.user.id),
        metadata={"username": result.user.username},
        request_id=request.state.request_id,
    )
    db.commit()
    logger.info("New user registered: %s", result.user.username)
    return result


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


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    user = db.scalar(select(User).where(User.username == identifier))
    if user is not None:
        return user
    return db.scalar(select(User).where(User.email == identifier))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Request a password-reset token.

    The response is identical whether or not the account exists (no account
    enumeration). In development the plaintext token is returned in the response
    so the full flow is testable; in production the token would be delivered by
    the configured notification channel instead of the response body.
    """
    user = _find_user_by_identifier(db, payload.identifier)
    dev_token: str | None = None
    if user is not None and user.is_active:
        dev_token = auth_service.create_password_reset_token(db, user)
        audit_service.record_audit(
            db,
            actor_id=user.id,
            action="auth.password_reset_requested",
            entity_type="user",
            entity_id=str(user.id),
            request_id=request.state.request_id,
        )
        db.commit()
        logger.info("Password reset requested for %s", user.username)
    elif user is not None and not user.is_active:
        logger.info("Password reset requested for inactive account")
    else:
        logger.info("Password reset requested for unknown identifier")

    message = (
        "If an account exists for that identifier, password reset instructions "
        "have been sent."
    )
    if settings.is_production:
        return ForgotPasswordResponse(message=message)
    # Development-only affordance: the reset token is echoed back so the flow is
    # exercisable end-to-end without an email provider. Never shipped to prod.
    return ForgotPasswordResponse(message=message, dev_reset_token=dev_token)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Consume a reset token and set a new password."""
    try:
        user = auth_service.reset_password_with_token(
            db, payload.token, payload.new_password
        )
    except auth_service.InvalidResetTokenError:
        audit_service.record_audit(
            db,
            actor_id=None,
            action="auth.password_reset.failed",
            entity_type="user",
            metadata={"reason": "token_invalid"},
            request_id=request.state.request_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    audit_service.record_audit(
        db,
        actor_id=user.id,
        action="auth.password_reset",
        entity_type="user",
        entity_id=str(user.id),
        request_id=request.state.request_id,
    )
    db.commit()
    return MessageResponse(message="Password has been reset. You can now sign in.")
