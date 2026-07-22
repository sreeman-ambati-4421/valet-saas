import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import twilio_client
from app.models.parking import QRCode, TagStatus
from app.models.session import SessionState, ValetSession
from app.models.tenant import Venue
from app.models.vehicle_guest import Guest
from app.schemas.session import SessionCreate
from app.services import session_service

RETRIEVAL_KEYWORDS = {"car", "retrieve", "pickup", "pick up"}

TERMINAL_STATES = {SessionState.COMPLETED, SessionState.CANCELLED}

# Matches the tag's pre-filled scan message, e.g. "Hi Kondapur Branch! My
# car needs to be parked -- tag A1B3F0." -- anchored to the tag's actual
# 6-hex-char format so casual mentions of the word "tag" elsewhere in a
# guest's message can't be mistaken for a scan.
CODE_PATTERN = re.compile(r"\btag\s+([0-9A-Fa-f]{6})\b", re.IGNORECASE)


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

    code_match = CODE_PATTERN.search(text)
    if code_match:
        await _handle_qr_scan(db, guest, code_match.group(1).upper())
        return

    await _handle_general_message(db, guest, text)


async def _handle_qr_scan(db: AsyncSession, guest: Guest, token: str) -> None:
    result = await db.execute(select(QRCode).where(QRCode.token == token, QRCode.is_active.is_(True)))
    qr = result.scalar_one_or_none()
    if qr is None:
        _reply(
            guest.whatsapp_phone_number,
            "*⚠️ Invalid Tag*\nSorry, this tag isn't valid. Please ask a staff member for help.",
        )
        return

    if qr.status != TagStatus.AVAILABLE:
        _reply(
            guest.whatsapp_phone_number,
            "*⚠️ Tag In Use*\nSorry, this tag is currently in use. Please ask a staff member for help.",
        )
        return

    venue = await db.get(Venue, qr.venue_id)
    data = SessionCreate(guest_phone_number=guest.whatsapp_phone_number, guest_name=guest.name, qr_code_id=qr.id)
    try:
        await session_service.create_session(db, venue.tenant_id, venue.id, None, data, created_via_whatsapp=True)
    except HTTPException:
        # Lost a race against someone else claiming the same tag in the
        # instant between our availability check and actually claiming it.
        _reply(
            guest.whatsapp_phone_number,
            "*⚠️ Tag Just Claimed*\nSorry, that tag was just claimed by someone else. Please ask a staff member "
            "for help.",
        )
        return

    _reply(
        guest.whatsapp_phone_number,
        f"*✅ Request Received*\nWelcome to {venue.name if venue else 'our valet service'}! We've got your "
        "request -- a valet will be with you shortly. We'll text you once it's parked.",
    )


async def _handle_general_message(db: AsyncSession, guest: Guest, text: str) -> None:
    session = await _get_active_session(db, guest.id)

    if session is None:
        _reply(guest.whatsapp_phone_number, "Scan the tag at the venue to start a valet request.")
        return

    if text.lower() in RETRIEVAL_KEYWORDS and session.state == SessionState.PARKED:
        await session_service.transition_session(
            db, session, SessionState.RETRIEVAL_REQUESTED, None, note="Guest requested retrieval via WhatsApp"
        )
        _reply(
            guest.whatsapp_phone_number,
            "*✅ Request Confirmed*\nWe've received your request -- a driver will be dispatched shortly.",
        )
        return

    _reply(
        guest.whatsapp_phone_number,
        f"*ℹ️ Status Update*\nYour car's current status: {session.state.value.replace('_', ' ').title()}.",
    )
