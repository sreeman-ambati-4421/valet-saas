import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import supabase_admin, twilio_client
from app.core.config import settings
from app.core.supabase_admin import StaffInviteError
from app.models.user import User, UserRole, UserVenueAccess

logger = logging.getLogger(__name__)


async def create_invited_user(
    db: AsyncSession,
    phone_number: str,
    full_name: str,
    role: UserRole,
    tenant_id: str | None,
    venue_id: str | None = None,
) -> User:
    """Grants a new staff member access, identified by their phone number.

    Creates a phone-confirmed Supabase Auth account (no invite link/token --
    they log in with an SMS OTP sent straight to that number, so simply
    receiving it proves ownership) and sends a WhatsApp notification (the
    invite notification itself; login codes arrive by SMS) telling them to
    sign in.

    tenant_id/venue_id must already be resolved by the caller from
    server-side context (the target venue/tenant), never taken directly
    from client input for this field.
    """
    existing = await db.execute(select(User).where(User.phone_number == phone_number))
    if existing.scalar_one_or_none() is not None:
        raise StaffInviteError(f"A user with phone number {phone_number} is already invited or registered.")

    supabase_user_id = supabase_admin.create_phone_confirmed_user(phone_number, full_name)

    user = User(
        supabase_user_id=supabase_user_id,
        tenant_id=tenant_id,
        phone_number=phone_number,
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
            "Supabase account creation succeeded (user_id=%s, phone=%s) but creating "
            "the app-level user row failed -- the Supabase Auth user now exists "
            "without a matching users row and needs manual cleanup.",
            supabase_user_id,
            phone_number,
        )
        raise

    await db.refresh(user)

    twilio_client.send_whatsapp_text(
        phone_number,
        f"Hi {full_name}, you now have access to the Valet Parking platform. "
        f"Sign in with this phone number at {settings.frontend_url}/login to get started.",
    )

    return user
