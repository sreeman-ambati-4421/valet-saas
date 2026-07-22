import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import supabase_admin, twilio_client
from app.core.config import settings
from app.core.security import create_invite_token
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

    Creates a phone-confirmed but password-less Supabase Auth account, and
    sends a WhatsApp message containing a one-time accept-invite link. The
    link carries our own signed token (not a Supabase one -- phone-identified
    accounts have no Supabase "magic link" equivalent), so simply viewing it
    does nothing; the password is only set, and the account only activated,
    when the recipient submits it via the accept-invite form.

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
        # Stays inactive until they accept the invite and set a password --
        # an unaccepted invite must not be indistinguishable from a real
        # active staff member.
        is_active=False,
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

    invite_token = create_invite_token(user.id)
    accept_url = f"{settings.frontend_url}/accept-invite?token={invite_token}"
    twilio_client.send_whatsapp_text(
        phone_number,
        f"Hi {full_name}, you've been invited to the Valet Parking platform. "
        f"Tap this link to set your password and get started: {accept_url}",
    )

    return user
