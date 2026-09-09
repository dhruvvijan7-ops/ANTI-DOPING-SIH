"""password_reset_tokens

Revision ID: 0004_password_reset
Revises: 0003_evidence_integrity
Create Date: 2026-09-09

Phase G/H authentication update: secure self-service password reset.

New table password_reset_tokens:
- token_hash: SHA-256 digest of the opaque reset token (never stored in
  plaintext, mirrors the "no plaintext secrets at rest" rule).
- expires_at: short-lived window (default 30 minutes).
- used_at: enforces single-use (one-time) consumption.
- user_id FK CASCADE so removing a user removes their pending tokens.
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_password_reset"
down_revision = "0003_evidence_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_reset_tokens_token_hash"), "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_password_reset_tokens_user_id"), "password_reset_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_index(op.f("ix_password_reset_tokens_token_hash"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")