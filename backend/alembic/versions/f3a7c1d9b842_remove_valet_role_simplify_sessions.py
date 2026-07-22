"""remove valet driver role, simplify session state machine

Revision ID: f3a7c1d9b842
Revises: 6cf9b9967484
Create Date: 2026-07-22

Product change: valet drivers are never system users -- a single valet_desk
person coordinates them verbally and reports outcomes over WhatsApp. This
collapses the 4-role model into 3 (platform_super_admin -> saas_owner;
tenant_admin/venue_manager merge into business_owner; valet -> valet_desk)
and drops the physical-handling states VEHICLE_COLLECTED/DELIVERED from the
session state machine, since no one reports those individually anymore.

venue_manager -> business_owner is a real semantic widening (venue-scoped
access becomes tenant-wide) but there is no narrower target role left to
map it to.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f3a7c1d9b842"
down_revision: Union[str, None] = "6cf9b9967484"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_check_constraint(table: str, column: str, allowed_values: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    drop_sql = f"""
    DO $$
    DECLARE
        existing_constraint text;
    BEGIN
        SELECT con.conname INTO existing_constraint
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
        WHERE rel.relname = '{table}' AND att.attname = '{column}' AND con.contype = 'c';

        IF existing_constraint IS NOT NULL THEN
            EXECUTE 'ALTER TABLE {table} DROP CONSTRAINT ' || quote_ident(existing_constraint);
        END IF;
    END $$;
    """
    op.execute(drop_sql)
    values_sql = ",".join(f"'{v}'" for v in allowed_values)
    op.create_check_constraint(f"{table}_{column}", table, f"{column} IN ({values_sql})")


NEW_ROLES = ("saas_owner", "business_owner", "valet_desk")
OLD_ROLES = ("platform_super_admin", "tenant_admin", "venue_manager", "valet")

NEW_STATES = ("REQUESTED", "ACCEPTED", "PARKED", "RETRIEVAL_REQUESTED", "RETRIEVING", "READY", "COMPLETED", "CANCELLED")
OLD_STATES = (
    "REQUESTED",
    "ASSIGNED",
    "VEHICLE_COLLECTED",
    "PARKED",
    "RETRIEVAL_REQUESTED",
    "RETRIEVING",
    "READY",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
)


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'saas_owner' WHERE role = 'platform_super_admin'")
    op.execute("UPDATE users SET role = 'business_owner' WHERE role IN ('tenant_admin', 'venue_manager')")
    op.execute("UPDATE users SET role = 'valet_desk' WHERE role = 'valet'")
    _replace_check_constraint("users", "role", NEW_ROLES)

    op.execute("UPDATE valet_sessions SET state = 'ACCEPTED' WHERE state IN ('ASSIGNED', 'VEHICLE_COLLECTED')")
    op.execute("UPDATE valet_sessions SET state = 'COMPLETED' WHERE state = 'DELIVERED'")
    _replace_check_constraint("valet_sessions", "state", NEW_STATES)

    op.execute("UPDATE session_events SET from_state = 'ACCEPTED' WHERE from_state IN ('ASSIGNED', 'VEHICLE_COLLECTED')")
    op.execute("UPDATE session_events SET to_state = 'ACCEPTED' WHERE to_state IN ('ASSIGNED', 'VEHICLE_COLLECTED')")
    op.execute("UPDATE session_events SET from_state = 'COMPLETED' WHERE from_state = 'DELIVERED'")
    op.execute("UPDATE session_events SET to_state = 'COMPLETED' WHERE to_state = 'DELIVERED'")

    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.alter_column("assigned_valet_id", new_column_name="accepted_by_user_id")
    # The rename above carries the index along under its old name (SQLite's
    # batch-recreate) or leaves it untouched (Postgres plain ALTER) -- drop
    # and recreate it explicitly so the name matches the column everywhere.
    op.drop_index("ix_valet_sessions_assigned_valet_id", table_name="valet_sessions")
    op.create_index("ix_valet_sessions_accepted_by_user_id", "valet_sessions", ["accepted_by_user_id"])


def downgrade() -> None:
    with op.batch_alter_table("valet_sessions") as batch_op:
        batch_op.alter_column("accepted_by_user_id", new_column_name="assigned_valet_id")
    op.drop_index("ix_valet_sessions_accepted_by_user_id", table_name="valet_sessions")
    op.create_index("ix_valet_sessions_assigned_valet_id", "valet_sessions", ["assigned_valet_id"])

    # Lossy: ACCEPTED collapses back to ASSIGNED (VEHICLE_COLLECTED distinction is gone),
    # COMPLETED that originated from READY collapses back to DELIVERED.
    op.execute("UPDATE session_events SET from_state = 'ASSIGNED' WHERE from_state = 'ACCEPTED'")
    op.execute("UPDATE session_events SET to_state = 'ASSIGNED' WHERE to_state = 'ACCEPTED'")
    op.execute("UPDATE session_events SET from_state = 'DELIVERED' WHERE from_state = 'COMPLETED'")
    op.execute("UPDATE session_events SET to_state = 'DELIVERED' WHERE to_state = 'COMPLETED'")

    op.execute("UPDATE valet_sessions SET state = 'ASSIGNED' WHERE state = 'ACCEPTED'")
    op.execute("UPDATE valet_sessions SET state = 'DELIVERED' WHERE state = 'COMPLETED'")
    _replace_check_constraint("valet_sessions", "state", OLD_STATES)

    # Lossy: business_owner cannot be un-merged back into tenant_admin vs. venue_manager.
    op.execute("UPDATE users SET role = 'platform_super_admin' WHERE role = 'saas_owner'")
    op.execute("UPDATE users SET role = 'tenant_admin' WHERE role = 'business_owner'")
    op.execute("UPDATE users SET role = 'valet' WHERE role = 'valet_desk'")
    _replace_check_constraint("users", "role", OLD_ROLES)
