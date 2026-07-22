import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import twilio_client
from app.models.session import SessionState, ValetSession
from app.models.user import User, UserRole, UserVenueAccess
from app.models.vehicle_guest import Vehicle
from app.services import session_service

# Only "ACCEPT" is handled remotely -- every later step (park, ready, etc.)
# requires being physically at the vehicle anyway, so there's nothing to
# gain from also supporting those over WhatsApp.
ACCEPT_PATTERN = re.compile(r"^ACCEPT-([A-Z0-9]{6})$", re.IGNORECASE)


def _reply(to: str, body: str) -> None:
    twilio_client.send_whatsapp_text(to, body)


async def find_staff_user(db: AsyncSession, phone_number: str) -> User | None:
    """Distinguishes a staff sender from a guest one -- checked before any
    inbound message is assumed to be a guest starting/continuing a valet
    conversation, so a staff member's own number never accidentally creates
    a guest session."""
    result = await db.execute(select(User).where(User.phone_number == phone_number, User.is_active.is_(True)))
    return result.scalar_one_or_none()


async def handle_inbound_message(db: AsyncSession, user: User, body: str) -> None:
    match = ACCEPT_PATTERN.match(body.strip())
    if not match:
        # Not a recognized staff command -- stay silent rather than guess
        # what they meant.
        return

    if user.role != UserRole.VALET_DESK:
        _reply(user.phone_number, "Only valet desk staff can accept requests this way.")
        return

    code = match.group(1).upper()
    venue_ids_result = await db.execute(
        select(UserVenueAccess.venue_id).where(UserVenueAccess.user_id == user.id)
    )
    venue_ids = [row[0] for row in venue_ids_result.all()]
    if not venue_ids:
        _reply(user.phone_number, "You don't have access to any venues yet.")
        return

    candidates_result = await db.execute(
        select(ValetSession).where(
            ValetSession.venue_id.in_(venue_ids),
            ValetSession.state == SessionState.REQUESTED,
            ValetSession.accepted_by_user_id.is_(None),
        )
    )
    session = next(
        (s for s in candidates_result.scalars().all() if session_service.short_code(s.id) == code), None
    )
    if session is None:
        _reply(user.phone_number, "That request code wasn't found or has already been claimed.")
        return

    try:
        accepted = await session_service.accept_session(db, session.id, user)
    except HTTPException:
        _reply(user.phone_number, "Someone else already claimed that request.")
        return

    vehicle = await db.get(Vehicle, accepted.vehicle_id)
    reg = vehicle.registration_number if vehicle else "the vehicle"
    _reply(user.phone_number, f"You've got it -- {reg}.")
