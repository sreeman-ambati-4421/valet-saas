from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import whatsapp_client
from app.models.parking import QRCode, TagStatus
from app.models.session import ALLOWED_TRANSITIONS, SessionEvent, SessionState, ValetSession
from app.models.user import User, UserRole, UserVenueAccess
from app.models.vehicle_guest import Guest, Vehicle
from app.schemas.session import ParkInput, SessionCreate

TAG_NOT_AVAILABLE_DETAIL = "That tag is not available."

GUEST_STATUS_MESSAGES = {
    SessionState.PARKED: (
        "*🅿️ Vehicle Parked*\nYour vehicle has been parked safely. Reply 'car' anytime you're ready to have "
        "it brought back."
    ),
    SessionState.RETRIEVING: "*🚗 On The Way*\nYour vehicle is on the way to you now.",
    SessionState.READY: "*🎉 Ready for Pickup!*\nYour car is ready and waiting for you.",
}


async def _notify_guest_of_status(db: AsyncSession, session: ValetSession, to_state: SessionState) -> None:
    message = GUEST_STATUS_MESSAGES.get(to_state)
    if message is None:
        return
    guest = await db.get(Guest, session.guest_id)
    if guest is not None:
        whatsapp_client.send_whatsapp_text(guest.whatsapp_phone_number, message)


def normalize_registration(raw: str) -> str:
    return "".join(raw.split()).upper()


def short_code(session_id: str) -> str:
    """A human-typeable stand-in for a session's full UUID, used in the
    "reply ACCEPT-<code>" WhatsApp notification -- not stored separately,
    just derived from the id whenever needed."""
    return session_id.replace("-", "").upper()[-6:]


async def _notify_desk_staff_of_new_request(db: AsyncSession, session: ValetSession) -> None:
    tag = await db.get(QRCode, session.qr_code_id) if session.qr_code_id else None
    tag_label = tag.label if tag else "a vehicle"
    result = await db.execute(
        select(User)
        .join(UserVenueAccess, UserVenueAccess.user_id == User.id)
        .where(
            UserVenueAccess.venue_id == session.venue_id,
            User.role == UserRole.VALET_DESK,
            User.is_active.is_(True),
        )
    )
    for desk_user in result.scalars().all():
        whatsapp_client.send_whatsapp_text(
            desk_user.phone_number,
            f"*🔔 New Request*\n{tag_label}. Reply ACCEPT-{short_code(session.id)} to claim it, or open the app.",
        )


async def get_or_create_guest(db: AsyncSession, phone_number: str, name: str | None) -> Guest:
    result = await db.execute(select(Guest).where(Guest.whatsapp_phone_number == phone_number))
    guest = result.scalar_one_or_none()
    if guest is None:
        guest = Guest(whatsapp_phone_number=phone_number, name=name)
        db.add(guest)
        await db.flush()
    return guest


async def get_or_create_vehicle(db: AsyncSession, registration_number: str) -> Vehicle:
    normalized = normalize_registration(registration_number)
    result = await db.execute(select(Vehicle).where(Vehicle.registration_number == normalized))
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        vehicle = Vehicle(registration_number=normalized)
        db.add(vehicle)
        await db.flush()
    return vehicle


async def record_event(
    db: AsyncSession,
    session: ValetSession,
    from_state: SessionState | None,
    to_state: SessionState,
    actor: User | None,
    note: str | None = None,
) -> None:
    db.add(
        SessionEvent(
            session_id=session.id,
            actor_user_id=actor.id if actor else None,
            from_state=from_state.value if from_state else None,
            to_state=to_state.value,
            note=note,
        )
    )


async def _claim_tag(db: AsyncSession, venue_id: str, qr_code_id: str | None) -> QRCode:
    """Atomically marks a tag IN_USE so two simultaneous claims (a guest
    scan racing a staff-created request, or two staff creating sessions at
    once) can't both attach to the same physical tag.

    If qr_code_id is given (a guest scanned a specific tag), only that one
    is considered. Otherwise (staff-created session, no scan happened) any
    available tag for the venue is auto-assigned.
    """
    if qr_code_id is not None:
        result = await db.execute(
            update(QRCode)
            .where(QRCode.id == qr_code_id, QRCode.status == TagStatus.AVAILABLE, QRCode.is_active.is_(True))
            .values(status=TagStatus.IN_USE)
            .returning(QRCode)
        )
    else:
        candidate = await db.execute(
            select(QRCode.id)
            .where(QRCode.venue_id == venue_id, QRCode.status == TagStatus.AVAILABLE, QRCode.is_active.is_(True))
            .limit(1)
        )
        candidate_id = candidate.scalar_one_or_none()
        if candidate_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "No available tags for this venue.")
        result = await db.execute(
            update(QRCode)
            .where(QRCode.id == candidate_id, QRCode.status == TagStatus.AVAILABLE)
            .values(status=TagStatus.IN_USE)
            .returning(QRCode)
        )

    tag = result.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status.HTTP_409_CONFLICT, TAG_NOT_AVAILABLE_DETAIL)
    return tag


async def create_session(
    db: AsyncSession,
    tenant_id: str,
    venue_id: str,
    actor: User | None,
    data: SessionCreate,
    created_via_whatsapp: bool = False,
) -> ValetSession:
    guest = await get_or_create_guest(db, data.guest_phone_number, data.guest_name)
    tag = await _claim_tag(db, venue_id, data.qr_code_id)

    session = ValetSession(
        tenant_id=tenant_id,
        venue_id=venue_id,
        guest_id=guest.id,
        vehicle_id=None,
        qr_code_id=tag.id,
        state=SessionState.REQUESTED,
        created_via_whatsapp=created_via_whatsapp,
    )
    db.add(session)
    await db.flush()
    await record_event(db, session, None, SessionState.REQUESTED, actor, note="Session created")
    await db.commit()
    await db.refresh(session)
    await _notify_desk_staff_of_new_request(db, session)
    return session


async def get_session_or_404(db: AsyncSession, session_id: str) -> ValetSession:
    result = await db.execute(select(ValetSession).where(ValetSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


async def accept_session(db: AsyncSession, session_id: str, desk_user: User) -> ValetSession:
    """Atomic conditional accept: only succeeds if the session is still REQUESTED
    and unaccepted, so two desk-person taps at once can't both win (BRD FR-07)."""
    result = await db.execute(
        update(ValetSession)
        .where(
            ValetSession.id == session_id,
            ValetSession.state == SessionState.REQUESTED,
            ValetSession.accepted_by_user_id.is_(None),
        )
        .values(accepted_by_user_id=desk_user.id, state=SessionState.ACCEPTED)
        .returning(ValetSession)
    )
    session = result.scalar_one_or_none()
    if session is None:
        # Distinguish "doesn't exist" from "already taken" for a clearer error.
        await get_session_or_404(db, session_id)
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already accepted or not awaiting acceptance")

    await record_event(db, session, SessionState.REQUESTED, SessionState.ACCEPTED, desk_user, note="Job accepted")
    await db.commit()
    await db.refresh(session)
    return session


TAG_RELEASED_ON_STATES = {SessionState.COMPLETED, SessionState.CANCELLED}


async def transition_session(
    db: AsyncSession,
    session: ValetSession,
    to_state: SessionState,
    actor: User | None,
    note: str | None = None,
    park_input: ParkInput | None = None,
) -> ValetSession:
    if to_state not in ALLOWED_TRANSITIONS.get(session.state, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move session from {session.state.value} to {to_state.value}",
        )

    from_state = session.state
    if park_input is not None:
        vehicle = await get_or_create_vehicle(db, park_input.registration_number)
        session.vehicle_id = vehicle.id

    session.state = to_state
    await record_event(db, session, from_state, to_state, actor, note=note)

    if to_state in TAG_RELEASED_ON_STATES and session.qr_code_id:
        await db.execute(update(QRCode).where(QRCode.id == session.qr_code_id).values(status=TagStatus.AVAILABLE))

    await db.commit()
    await db.refresh(session)

    await _notify_guest_of_status(db, session, to_state)
    return session
