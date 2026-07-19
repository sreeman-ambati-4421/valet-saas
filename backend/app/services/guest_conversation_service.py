from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import twilio_client
from app.models.parking import QRCode
from app.models.session import SessionState, ValetSession
from app.models.tenant import Venue
from app.models.vehicle_guest import Guest
from app.schemas.session import SessionCreate
from app.services import session_service

RETRIEVAL_KEYWORDS = {"car", "retrieve", "pickup", "pick up"}

TERMINAL_STATES = {SessionState.DELIVERED, SessionState.COMPLETED, SessionState.CANCELLED}


async def _get_active_session(db: AsyncSession, guest_id: str) -> ValetSession | None:
    result = await db.execute(
        select(ValetSession)
        .where(ValetSession.guest_id == guest_id, ValetSession.state.not_in(TERMINAL_STATES))
        .order_by(ValetSession.created_at.desc())
    )
    return result.scalars().first()


def _reply(to: str, body: str) -> None:
    twilio_client.send_whatsapp_text(to, body)


async def handle_inbound_message(db: AsyncSession, from_phone: str, body: str) -> None:
    text = body.strip()
    guest = await session_service.get_or_create_guest(db, from_phone, None)
    await db.commit()
    await db.refresh(guest)

    if guest.pending_venue_id:
        await _handle_reg_number_reply(db, guest, text)
        return

    if text.upper().startswith("QR:"):
        await _handle_qr_scan(db, guest, text[3:].strip())
        return

    await _handle_general_message(db, guest, text)


async def _handle_qr_scan(db: AsyncSession, guest: Guest, token: str) -> None:
    result = await db.execute(select(QRCode).where(QRCode.token == token, QRCode.is_active.is_(True)))
    qr = result.scalar_one_or_none()
    if qr is None:
        _reply(guest.whatsapp_phone_number, "Sorry, this QR code isn't valid. Please ask a staff member for help.")
        return

    venue = await db.get(Venue, qr.venue_id)
    guest.pending_venue_id = qr.venue_id
    await db.commit()

    _reply(
        guest.whatsapp_phone_number,
        f"Welcome to {venue.name if venue else 'our valet service'}! Please reply with your vehicle's "
        "registration number to start.",
    )


async def _handle_reg_number_reply(db: AsyncSession, guest: Guest, reg_number: str) -> None:
    venue_id = guest.pending_venue_id
    venue = await db.get(Venue, venue_id)
    if venue is None or not reg_number:
        _reply(guest.whatsapp_phone_number, "Something went wrong -- please scan the QR code again.")
        guest.pending_venue_id = None
        await db.commit()
        return

    data = SessionCreate(registration_number=reg_number, guest_phone_number=guest.whatsapp_phone_number, guest_name=guest.name)
    await session_service.create_session(db, venue.tenant_id, venue_id, None, data)

    guest.pending_venue_id = None
    await db.commit()

    _reply(
        guest.whatsapp_phone_number,
        f"Got it -- {session_service.normalize_registration(reg_number)}. We'll text you updates. "
        "Reply 'car' anytime you're ready to have it brought back.",
    )


async def _handle_general_message(db: AsyncSession, guest: Guest, text: str) -> None:
    session = await _get_active_session(db, guest.id)

    if session is None:
        _reply(guest.whatsapp_phone_number, "Scan the QR code at the venue to start a valet request.")
        return

    if text.lower() in RETRIEVAL_KEYWORDS and session.state == SessionState.PARKED:
        await session_service.transition_session(
            db, session, SessionState.RETRIEVAL_REQUESTED, None, note="Guest requested retrieval via WhatsApp"
        )
        _reply(guest.whatsapp_phone_number, "Got it! We're bringing your car around now.")
        return

    _reply(
        guest.whatsapp_phone_number,
        f"Your car's current status: {session.state.value.replace('_', ' ').title()}.",
    )
