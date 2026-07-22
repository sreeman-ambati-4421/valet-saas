"""drop unused tables and columns

Revision ID: a3f7d8c2e415
Revises: e91a4c2b7f10
Create Date: 2026-07-25

Removes schema that was never actually wired up to any code path:
- parking_zones / parking_slots: no API ever managed these; location
  tracking lives in the physical key tag now, not a digital zone/slot.
- whatsapp_accounts: Twilio config is a single global account via env
  vars, never per-tenant DB rows.
- subscriptions: billing was never built (BRD marked it "Could" priority).
- valet_sessions.parking_zone_id / parking_slot_id: always null, nothing
  left for them to reference once the zone/slot tables are gone.
- vehicles.make / model / color: declared but never read or written by
  any code path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f7d8c2e415"
down_revision: Union[str, None] = "e91a4c2b7f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.drop_column("parking_zone_id")
        batch_op.drop_column("parking_slot_id")

    op.drop_index("ix_parking_slots_zone_id", table_name="parking_slots")
    op.drop_table("parking_slots")

    op.drop_index("ix_parking_zones_venue_id", table_name="parking_zones")
    op.drop_table("parking_zones")

    op.drop_index("ix_whatsapp_accounts_tenant_id", table_name="whatsapp_accounts")
    op.drop_table("whatsapp_accounts")

    op.drop_index("ix_subscriptions_tenant_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.drop_column("make")
        batch_op.drop_column("model")
        batch_op.drop_column("color")


def downgrade() -> None:
    with op.batch_alter_table("vehicles") as batch_op:
        batch_op.add_column(sa.Column("color", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("model", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("make", sa.String(length=64), nullable=True))

    op.create_table(
        "subscriptions",
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("venue_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"], unique=False)

    op.create_table(
        "whatsapp_accounts",
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("twilio_whatsapp_number", sa.String(length=32), nullable=True),
        sa.Column("twilio_account_sid", sa.String(length=64), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whatsapp_accounts_tenant_id", "whatsapp_accounts", ["tenant_id"], unique=False)

    op.create_table(
        "parking_zones",
        sa.Column("venue_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parking_zones_venue_id", "parking_zones", ["venue_id"], unique=False)

    op.create_table(
        "parking_slots",
        sa.Column("zone_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("is_occupied", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["parking_zones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parking_slots_zone_id", "parking_slots", ["zone_id"], unique=False)

    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.add_column(sa.Column("parking_slot_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("parking_zone_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_valet_sessions_parking_zone_id", "parking_zones", ["parking_zone_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_valet_sessions_parking_slot_id", "parking_slots", ["parking_slot_id"], ["id"]
        )
