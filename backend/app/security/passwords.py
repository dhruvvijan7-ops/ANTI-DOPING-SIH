"""Password hashing utilities.

Uses bcrypt directly (not passlib) for compatibility with the installed Python
runtime and to avoid passlib/bcrypt version drift. Passwords are never stored in
plaintext (FR-AUTH-003).
"""
from __future__ import annotations

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with a per-password salt."""
    if plain_password is None or plain_password == "":
        raise ValueError("Password must not be empty")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
