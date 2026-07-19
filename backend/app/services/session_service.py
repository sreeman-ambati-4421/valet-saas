from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ALLOWED_TRANSITIONS, SessionEvent, SessionState, ValetSession
from app.models.user import User
from app.models.vehicle_guest import Guest, Vehicle
from app.schemas.session import ParkInput, SessionCreate


def normalize_registration(raw: str) -> str:
    return "".join(raw.split()).upper()


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


async def create_session(
    db: AsyncSession, tenant_id: str, venue_id: str, actor: User, data: SessionCreate
) -> ValetSession:
    guest = await get_or_create_guest(db, data.guest_phone_number, data.guest_name)
    vehicle = await get_or_create_vehicle(db, data.registration_number)

    session = ValetSession(
        tenant_id=tenant_id,
        venue_id=venue_id,
        guest_id=guest.id,
        vehicle_id=vehicle.id,
        state=SessionState.REQUESTED,
    )
    db.add(session)
    await db.flush()
    await record_event(db, session, None, SessionState.REQUESTED, actor, note="Session created")
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_or_404(db: AsyncSession, session_id: str) -> ValetSession:
    result = await db.execute(select(ValetSession).where(ValetSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


async def accept_session(db: AsyncSession, session_id: str, valet: User) -> ValetSession:
    """Atomic conditional accept: only succeeds if the session is still REQUESTED
    and unassigned, so two valets accepting at once can't both win (BRD FR-07)."""
    result = await db.execute(
        update(ValetSession)
        .where(
            ValetSession.id == session_id,
            ValetSession.state == SessionState.REQUESTED,
            ValetSession.assigned_valet_id.is_(None),
        )
        .values(assigned_valet_id=valet.id, state=SessionState.ASSIGNED)
        .returning(ValetSession)
    )
    session = result.scalar_one_or_none()
    if session is None:
        # Distinguish "doesn't exist" from "already taken" for a clearer error.
        await get_session_or_404(db, session_id)
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already accepted or not awaiting acceptance")

    await record_event(db, session, SessionState.REQUESTED, SessionState.ASSIGNED, valet, note="Job accepted")
    await db.commit()
    await db.refresh(session)
    return session


async def transition_session(
    db: AsyncSession,
    session: ValetSession,
    to_state: SessionState,
    actor: User,
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
        session.parking_zone_id = park_input.parking_zone_id
        session.parking_slot_id = park_input.parking_slot_id
        session.key_tag = park_input.key_tag

    session.state = to_state
    await record_event(db, session, from_state, to_state, actor, note=note)
    await db.commit()
    await db.refresh(session)
    return session
