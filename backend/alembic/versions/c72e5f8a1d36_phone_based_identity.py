"""replace email with phone_number as the user identity

Revision ID: c72e5f8a1d36
Revises: f3a7c1d9b842
Create Date: 2026-07-22

Product change: login/invite is now WhatsApp-number-based, not email-based.
Supabase Auth accounts move from email+password to phone+OTP (delivered via
Twilio Verify's WhatsApp channel, configured in the Supabase dashboard --
not something a migration can do). There is no data to carry over: this
project has no production users yet, so old email-identified rows are
simply dropped rather than backfilled with a placeholder phone number.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c72e5f8a1d36"
down_revision: Union[str, None] = "f3a7c1d9b842"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No pre-existing users can be carried forward without a real phone
    # number on file -- clear the table rather than leave rows that could
    # never satisfy the new NOT NULL UNIQUE constraint.
    op.execute("DELETE FROM users")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("email")
        batch_op.add_column(sa.Column("phone_number", sa.String(length=32), nullable=False))
        batch_op.create_index("ix_users_phone_number", ["phone_number"], unique=True)


def downgrade() -> None:
    op.execute("DELETE FROM users")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_phone_number")
        batch_op.drop_column("phone_number")
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=False))
        batch_op.create_index("ix_users_email", ["email"], unique=True)
