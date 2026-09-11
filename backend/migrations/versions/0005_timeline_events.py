"""timeline_events

Revision ID: 0005_timeline_events
Revises: 0004_password_reset
Create Date: 2026-09-10

Workspace gate: manual timeline reconstruction entries (human-authored). The
aggregated case timeline keeps engine events as their original records and adds
these entries as "MANUAL"-origin rows for analyst-authored event reconstruction.
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_timeline_events"
down_revision = "0004_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="MANUAL"),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timeline_events_investigation_id"), "timeline_events", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_timeline_events_occurred_at"), "timeline_events", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_timeline_events_occurred_at"), table_name="timeline_events")
    op.drop_index(op.f("ix_timeline_events_investigation_id"), table_name="timeline_events")
    op.drop_table("timeline_events")