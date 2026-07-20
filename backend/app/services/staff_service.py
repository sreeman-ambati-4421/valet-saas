import logging
import urllib.parse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import supabase_admin, twilio_client
from app.core.config import settings
from app.models.user import User, UserRole, UserVenueAccess

logger = logging.getLogger(__name__)


async def create_invited_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    phone_number: str,
    role: UserRole,
    tenant_id: str | None,
    venue_id: str | None = None,
) -> User:
    """Creates a Supabase-invited user (account still identified by email
    under the hood) and delivers the invite link over WhatsApp instead of
    Supabase's own email sending -- avoids Supabase's low free-tier email
    rate limit and deliverability issues entirely.

    tenant_id/venue_id must already be resolved by the caller from
    server-side context (the target venue/tenant), never taken directly
    from client input for this field.
    """
    redirect_to = f"{settings.frontend_url}/accept-invite"
    supabase_user_id, action_link = supabase_admin.create_invite_link(email, redirect_to)

    user = User(
        supabase_user_id=supabase_user_id,
        tenant_id=tenant_id,
        email=email,
        full_name=full_name,
        role=role,
        # Stays inactive until they actually set a password and hit
        # POST /me/confirm -- an unaccepted invite must not be
        # indistinguishable from a real active staff member.
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
            "Supabase invite succeeded (user_id=%s, email=%s) but creating the "
            "app-level user row failed -- the Supabase Auth user now exists "
            "without a matching users row and needs manual cleanup.",
            supabase_user_id,
            email,
        )
        raise

    await db.refresh(user)

    # Route through our own click-through page rather than sending the raw
    # Supabase link directly: WhatsApp auto-fetches links to generate a
    # preview card the moment the message arrives, which would otherwise
    # consume the single-use invite token before the recipient ever taps it.
    click_through_url = f"{settings.frontend_url}/invite-redirect?to={urllib.parse.quote(action_link, safe='')}"

    twilio_client.send_whatsapp_text(
        phone_number,
        f"Hi {full_name}, you've been invited to the Valet Parking platform. "
        f"Tap this link to set up your account: {click_through_url}",
    )

    return user
