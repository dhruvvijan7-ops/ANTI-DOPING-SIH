"""User & role administration endpoints (ADMINISTRATOR)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.core.config import settings
from app.db.session import get_db
from app.models.identity import Permission, Role, User
from app.schemas.auth import (
    MessageResponse,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
)
from app.security.passwords import hash_password
from app.security.rbac import Permissions
from app.services import audit_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_permissions(Permissions.USERS_MANAGE))],
)


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)) -> List[UserResponse]:
    users = db.scalars(select(User).order_by(User.username)).all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> UserResponse:
    role = db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role {payload.role_name} not found")

    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    audit_service.record_audit(
        db,
        actor_id=actor.id,
        action="users.create",
        entity_type="user",
        entity_id=str(user.id),
        metadata={"username": user.username, "role": role.name},
    )
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db)) -> List[RoleResponse]:
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> RoleResponse:
    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    db.flush()
    audit_service.record_audit(
        db,
        actor_id=actor.id,
        action="roles.create",
        entity_type="role",
        entity_id=str(role.id),
        metadata={"name": role.name},
    )
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: str,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> RoleResponse:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    if payload.description is not None:
        role.description = payload.description
    if payload.permission_keys is not None:
        perms = db.scalars(
            select(Permission).where(Permission.key.in_(payload.permission_keys))
        ).all()
        role.permissions = list(perms)
    db.add(role)
    db.flush()
    audit_service.record_audit(
        db,
        actor_id=actor.id,
        action="roles.update",
        entity_type="role",
        entity_id=str(role.id),
        metadata={"updated": payload.model_dump(exclude_unset=True)},
    )
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.get("/permissions", response_model=List[PermissionResponse])
def list_permissions(db: Session = Depends(get_db)) -> List[PermissionResponse]:
    perms = db.scalars(select(Permission).order_by(Permission.key)).all()
    return [PermissionResponse.model_validate(p) for p in perms]
