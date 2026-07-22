"""physical key tags replace fixed venue QR codes

Revision ID: e91a4c2b7f10
Revises: d84b1e6f9a02
Create Date: 2026-07-24

Product change: QR codes are now a pool of pre-printed, reusable physical
key tags (one per vehicle key set at a time), not a single fixed
venue/entrance QR. Registration number is now captured at the Mark Parked
step (from the driver) instead of from the guest at request time, since
the tag -- not the reg. number -- is what links guest to vehicle now.

No data is preserved across this migration (per product decision --
existing dev data is being wiped and started fresh).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e91a4c2b7f10"
down_revision: Union[str, None] = "d84b1e6f9a02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("qr_codes") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="available")
        )

    with op.batch_alter_table("guests") as batch_op:
        batch_op.drop_constraint("fk_guests_pending_venue_id", type_="foreignkey")
        batch_op.drop_column("pending_venue_id")

    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.alter_column("vehicle_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.drop_column("key_tag")


def downgrade() -> None:
    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.add_column(sa.Column("key_tag", sa.String(length=64), nullable=True))
        batch_op.alter_column("vehicle_id", existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table("guests") as batch_op:
        batch_op.add_column(sa.Column("pending_venue_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key("fk_guests_pending_venue_id", "venues", ["pending_venue_id"], ["id"])

    with op.batch_alter_table("qr_codes") as batch_op:
        batch_op.drop_column("status")
