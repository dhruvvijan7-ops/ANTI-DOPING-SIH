"""graph gate: new entity types + node features + relationship extensions

Revision ID: 0006_graph_gate
Revises: 0005_timeline_events
Create Date: 2026-09-10

Graph gate: add EVENT/COMPETITION/LOCATION/SOURCE entity tables for 98
relationship endpoint vocabulary.  Add relationship_node_features for
100 role assignment, 552 verification, 553 persisted positions.
Extend entity_relationships with 101 frequency, 108 notes, 552
verification, 105 soft-delete (deleted_at).
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_graph_gate"
down_revision = "0005_timeline_events"
branch_labels = None
depends_on = None


def _create_entity_table(name, columns):
    cols = []
    for col_name, col_type, nullable, *rest in columns:
        kw = {"nullable": nullable}
        if rest:
            kw["server_default"] = rest[0]
        cols.append(sa.Column(col_name, col_type, **kw))
    op.create_table(name, *cols)
    op.create_index(f"ix_{name}_name", name, ["name"])
    if any(c[0] == "external_ref" for c in columns):
        op.create_index(f"ix_{name}_external_ref", name, ["external_ref"])


def upgrade() -> None:
    _create_entity_table("events", [
        ("id", sa.Uuid(), False),
        ("external_ref", sa.String(64), True),
        ("name", sa.String(255), False),
        ("event_type", sa.String(64), True),
        ("location", sa.String(255), True),
        ("start_date", sa.Date(), True),
        ("end_date", sa.Date(), True),
        ("status", sa.String(32), False),
        ("created_at", sa.DateTime(timezone=True), False, sa.func.now()),
    ])
    _create_entity_table("competitions", [
        ("id", sa.Uuid(), False),
        ("external_ref", sa.String(64), True),
        ("name", sa.String(255), False),
        ("sport", sa.String(128), True),
        ("level", sa.String(64), True),
        ("location", sa.String(255), True),
        ("start_date", sa.Date(), True),
        ("end_date", sa.Date(), True),
        ("status", sa.String(32), False),
        ("created_at", sa.DateTime(timezone=True), False, sa.func.now()),
    ])
    _create_entity_table("locations", [
        ("id", sa.Uuid(), False),
        ("external_ref", sa.String(64), True),
        ("name", sa.String(255), False),
        ("country", sa.String(64), True),
        ("city", sa.String(128), True),
        ("location_type", sa.String(64), True),
        ("status", sa.String(32), False),
        ("created_at", sa.DateTime(timezone=True), False, sa.func.now()),
    ])
    _create_entity_table("sources", [
        ("id", sa.Uuid(), False),
        ("external_ref", sa.String(64), True),
        ("name", sa.String(255), False),
        ("source_type", sa.String(64), True),
        ("reliability", sa.String(16), True),
        ("status", sa.String(32), False),
        ("created_at", sa.DateTime(timezone=True), False, sa.func.now()),
    ])

    # --- relationship_node_features (100, 552, 553) --------------------
    op.create_table(
        "relationship_node_features",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("graph_role", sa.String(64), nullable=True),
        sa.Column("verification", sa.String(16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=True),
        sa.Column("position_y", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_node_features_key",
        "relationship_node_features",
        ["entity_type", "entity_id"],
        unique=True,
    )

    # --- Extend entity_relationships (101, 108, 552, 105) ---------------
    op.add_column("entity_relationships", sa.Column("frequency", sa.String(64), nullable=True))
    op.add_column("entity_relationships", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("entity_relationships", sa.Column("verification", sa.String(16), nullable=True, server_default="UNVERIFIED"))
    op.add_column("entity_relationships", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("entity_relationships", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column("entity_relationships", "updated_at")
    op.drop_column("entity_relationships", "deleted_at")
    op.drop_column("entity_relationships", "verification")
    op.drop_column("entity_relationships", "notes")
    op.drop_column("entity_relationships", "frequency")
    op.drop_table("relationship_node_features")
    for table in ("sources", "locations", "competitions", "events"):
        op.drop_index(f"ix_{table}_name", table_name=table)
        if table in ("events", "competitions", "locations", "sources"):
            op.drop_index(f"ix_{table}_external_ref", table_name=table)
        op.drop_table(table)
