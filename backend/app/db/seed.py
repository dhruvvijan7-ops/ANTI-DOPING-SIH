"""Development bootstrap: seed roles, permissions and users.

Runs idempotently at application startup when DEPLOY_INITIAL_USERS is enabled
(dev/test). This creates the RBAC baseline and the four role accounts used by the
frontend and demo. Not intended for production without review.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.identity import Permission, Role, User
from app.security.passwords import hash_password
from app.security.rbac import Permissions, Roles

logger = logging.getLogger("clean_sport.seed")

# role -> permission keys
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Roles.ADMINISTRATOR: [
        Permissions.USERS_MANAGE,
        Permissions.ROLES_MANAGE,
        Permissions.RULES_CONFIGURE,
        Permissions.MODELS_MANAGE,
        Permissions.CONFIGURATION_MANAGE,
        Permissions.AUDIT_READ,
        Permissions.INTELLIGENCE_READ,
        Permissions.INTELLIGENCE_CREATE,
        Permissions.INTELLIGENCE_MODIFY,
        Permissions.SOURCES_MANAGE,
        Permissions.ANALYSIS_RUN,
        Permissions.ANALYSIS_READ,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_REVIEW,
        Permissions.ALERTS_DISMISS,
        Permissions.ALERTS_CONVERT,
        Permissions.ATHLETES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_MODIFY,
        Permissions.INVESTIGATIONS_ASSIGN,
        Permissions.EVIDENCE_CREATE,
        Permissions.EVIDENCE_MODIFY,
        Permissions.REPORTS_GENERATE,
        Permissions.REPORTS_READ,
        Permissions.RESOURCES_READ,
    ],
    Roles.INVESTIGATOR: [
        Permissions.INTELLIGENCE_READ,
        Permissions.INTELLIGENCE_CREATE,
        Permissions.ANALYSIS_RUN,
        Permissions.ANALYSIS_READ,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_REVIEW,
        Permissions.ALERTS_DISMISS,
        Permissions.ALERTS_CONVERT,
        Permissions.ATHLETES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_MODIFY,
        Permissions.INVESTIGATIONS_ASSIGN,
        Permissions.EVIDENCE_CREATE,
        Permissions.EVIDENCE_MODIFY,
        Permissions.REPORTS_GENERATE,
        Permissions.REPORTS_READ,
        Permissions.AUDIT_READ,
        Permissions.RESOURCES_READ,
    ],
    Roles.INTELLIGENCE_ANALYST: [
        Permissions.INTELLIGENCE_READ,
        Permissions.INTELLIGENCE_CREATE,
        Permissions.SOURCES_MANAGE,
        Permissions.ANALYSIS_RUN,
        Permissions.ANALYSIS_READ,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_REVIEW,
        Permissions.ATHLETES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.EVIDENCE_CREATE,
        Permissions.REPORTS_READ,
        Permissions.RESOURCES_READ,
    ],
    Roles.VIEWER: [
        Permissions.INTELLIGENCE_READ,
        Permissions.ANALYSIS_READ,
        Permissions.ALERTS_READ,
        Permissions.ATHLETES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.REPORTS_READ,
        Permissions.AUDIT_READ,
        Permissions.RESOURCES_READ,
    ],
}

INITIAL_USERS = [
    {"username": "admin", "role": Roles.ADMINISTRATOR, "full_name": "System Administrator"},
    {"username": "investigator", "role": Roles.INVESTIGATOR, "full_name": "Demo Investigator"},
    {"username": "analyst", "role": Roles.INTELLIGENCE_ANALYST, "full_name": "Demo Analyst"},
    {"username": "viewer", "role": Roles.VIEWER, "full_name": "Demo Viewer"},
]

# Per-role passwords via env for dev clarity; falls back to username-based password.
DEFAULT_PASSWORDS: dict[str, str] = {}


def seed_roles_and_permissions(db: Session) -> None:
    """Create roles and permission keys idempotently."""
    # Permissions
    perm_objs: dict[str, Permission] = {}
    all_keys = sorted({k for perms in ROLE_PERMISSIONS.values() for k in perms})
    for key in all_keys:
        perm = db.scalar(select(Permission).where(Permission.key == key))
        if perm is None:
            perm = Permission(key=key, description=f"Permission {key}")
            db.add(perm)
            db.flush()
        perm_objs[key] = perm

    # Roles
    for role_name in Roles.ALL:
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            description = {
                Roles.ADMINISTRATOR: "Full platform administration",
                Roles.INVESTIGATOR: "Conduct and manage investigations",
                Roles.INTELLIGENCE_ANALYST: "Ingest, assess and analyze intelligence",
                Roles.VIEWER: "Read-only access to authorized records",
            }[role_name]
            role = Role(name=role_name, description=description)
            db.add(role)
            db.flush()
        granted = [perm_objs[k] for k in ROLE_PERMISSIONS[role_name]]
        role.permissions = granted

    db.commit()


def seed_users(db: Session) -> None:
    """Create development users for each role (idempotent)."""
    admin_role = db.scalar(select(Role).where(Role.name == Roles.ADMINISTRATOR))
    if admin_role is None:
        raise RuntimeError("Roles not seeded; call seed_roles_and_permissions first")

    for item in INITIAL_USERS:
        existing = db.scalar(select(User).where(User.username == item["username"]))
        if existing is not None:
            continue
        role = db.scalar(select(Role).where(Role.name == item["role"]))
        password = DEFAULT_PASSWORDS.get(item["username"], f"{item['username']}-Passw0rd!")
        if item["username"] == "admin":
            if not settings.initial_admin_password:
                raise RuntimeError(
                    "INITIAL_ADMIN_PASSWORD must be set when DEPLOY_INITIAL_USERS is enabled"
                )
            password = settings.initial_admin_password
        user = User(
            username=item["username"],
            full_name=item["full_name"],
            password_hash=hash_password(password),
            role_id=role.id,
            status="ACTIVE",
            is_active=True,
        )
        db.add(user)

    db.commit()


def run_seed(db: Session) -> None:
    seed_roles_and_permissions(db)
    seed_users(db)
    logger.info("RBAC seed complete")
