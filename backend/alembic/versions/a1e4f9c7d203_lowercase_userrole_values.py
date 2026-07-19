"""lowercase userrole stored values

Revision ID: a1e4f9c7d203
Revises: b899e208dfe2
Create Date: 2026-07-19

The role column's CHECK constraint was generated from the enum's uppercase
member NAMES (PLATFORM_SUPER_ADMIN, ...) instead of its lowercase VALUES
(platform_super_admin, ...), which is what the API/frontend actually use
everywhere else. This migration fixes existing data and the constraint to
match.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1e4f9c7d203"
down_revision: Union[str, None] = "b899e208dfe2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_VALUES = ("platform_super_admin", "tenant_admin", "venue_manager", "valet")


def upgrade() -> None:
    op.execute("UPDATE users SET role = lower(role)")
    # Named CHECK constraint drop/recreate only works reliably via reflection
    # on Postgres; SQLite (used for local dev/tests) doesn't preserve CHECK
    # constraint names the same way, and doesn't need this enforced locally.
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("userrole", "users", type_="check")
        op.create_check_constraint("userrole", "users", "role IN ('%s')" % "','".join(NEW_VALUES))


def downgrade() -> None:
    op.execute("UPDATE users SET role = upper(role)")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("userrole", "users", type_="check")
        op.create_check_constraint(
            "userrole",
            "users",
            "role IN ('PLATFORM_SUPER_ADMIN','TENANT_ADMIN','VENUE_MANAGER','VALET')",
        )
