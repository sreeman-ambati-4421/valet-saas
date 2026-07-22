"""add created_via_whatsapp to valet_sessions

Revision ID: d84b1e6f9a02
Revises: c72e5f8a1d36
Create Date: 2026-07-23

Distinguishes guest-initiated (QR scan + WhatsApp) sessions from
staff-created ones, so retrieval requests on WhatsApp-originated sessions
can be restricted to the guest's own "car" message rather than a manual
staff button.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d84b1e6f9a02"
down_revision: Union[str, None] = "c72e5f8a1d36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("created_via_whatsapp", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.drop_column("created_via_whatsapp")
