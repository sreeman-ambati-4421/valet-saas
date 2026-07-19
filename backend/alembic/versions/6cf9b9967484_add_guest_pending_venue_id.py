"""add guest pending_venue_id

Revision ID: 6cf9b9967484
Revises: a1e4f9c7d203
Create Date: 2026-07-19 16:57:39.785000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6cf9b9967484'
down_revision: Union[str, None] = 'a1e4f9c7d203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("guests") as batch_op:
        batch_op.add_column(sa.Column("pending_venue_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key("fk_guests_pending_venue_id", "venues", ["pending_venue_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("guests") as batch_op:
        batch_op.drop_constraint("fk_guests_pending_venue_id", type_="foreignkey")
        batch_op.drop_column("pending_venue_id")
