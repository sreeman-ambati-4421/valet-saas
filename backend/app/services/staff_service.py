import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import supabase_admin
from app.core.config import settings
from app.models.user import User, UserRole, UserVenueAccess

logger = logging.getLogger(__name__)


async def create_invited_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    role: UserRole,
    tenant_id: str | None,
    venue_id: str | None = None,
) -> User:
    """Invites a user via Supabase Auth (email link to set their own
    password), then creates the matching app-level User row.

    tenant_id/venue_id must already be resolved by the caller from
    server-side context (the target venue/tenant), never taken directly
    from client input for this field.
    """
    redirect_to = f"{settings.frontend_url}/accept-invite"
    supabase_user_id = supabase_admin.invite_user(email, redirect_to)

    user = User(
        supabase_user_id=supabase_user_id,
        tenant_id=tenant_id,
        email=email,
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    try:
        await db.flush()
        if venue_id:
            db.add(UserVenueAccess(user_id=user.id, venue_id=venue_id))
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error(
            "Supabase invite succeeded (user_id=%s, email=%s) but creating the "
            "app-level user row failed -- the Supabase Auth user now exists "
            "without a matching users row and needs manual cleanup.",
            supabase_user_id,
            email,
        )
        raise

    await db.refresh(user)
    return user
