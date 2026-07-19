"""lowercase userrole stored values

Revision ID: a1e4f9c7d203
Revises: b899e208dfe2
Create Date: 2026-07-19

The role column's CHECK constraint was generated from the enum's uppercase
member NAMES (PLATFORM_SUPER_ADMIN, ...) instead of its lowercase VALUES
(platform_super_admin, ...), which is what the API/frontend actually use
everywhere else. This migration fixes existing data and the constraint to
match.

The constraint is looked up dynamically by column rather than by the
'userrole' name we originally asked SQLAlchemy for -- Postgres assigns its
own default name (e.g. users_role_check) for a CHECK generated inline in
CREATE TABLE, regardless of the name passed to Enum(), so hardcoding
'userrole' as the constraint name fails.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1e4f9c7d203"
down_revision: Union[str, None] = "b899e208dfe2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DROP_EXISTING_CHECK_SQL = """
DO $$
DECLARE
    existing_constraint text;
BEGIN
    SELECT con.conname INTO existing_constraint
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
    WHERE rel.relname = 'users' AND att.attname = 'role' AND con.contype = 'c';

    IF existing_constraint IS NOT NULL THEN
        EXECUTE 'ALTER TABLE users DROP CONSTRAINT ' || quote_ident(existing_constraint);
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute("UPDATE users SET role = lower(role)")
    # SQLite (local dev/tests) doesn't need this enforced the same way, and
    # doesn't support the pg_constraint lookup below.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(_DROP_EXISTING_CHECK_SQL)
        op.create_check_constraint(
            "userrole",
            "users",
            "role IN ('platform_super_admin','tenant_admin','venue_manager','valet')",
        )


def downgrade() -> None:
    op.execute("UPDATE users SET role = upper(role)")
    if op.get_bind().dialect.name == "postgresql":
        op.execute(_DROP_EXISTING_CHECK_SQL)
        op.create_check_constraint(
            "userrole",
            "users",
            "role IN ('PLATFORM_SUPER_ADMIN','TENANT_ADMIN','VENUE_MANAGER','VALET')",
        )
