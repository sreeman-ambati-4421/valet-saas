from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import get_current_user, require_role, require_venue_access
from app.models.session import SessionState, ValetSession
from app.models.tenant import Venue
from app.models.user import User, UserRole
from app.models.vehicle_guest import Guest, Vehicle
from app.schemas.session import ParkInput, SessionCreate, SessionDetailOut, SessionOut
from app.services import session_service

router = APIRouter(tags=["sessions"])

STAFF_ROLES = (UserRole.VALET_DESK, UserRole.BUSINESS_OWNER, UserRole.SAAS_OWNER)
ADMIN_OVERRIDE_ROLES = (UserRole.BUSINESS_OWNER, UserRole.SAAS_OWNER)


async def _enrich(db: AsyncSession, session: ValetSession) -> SessionOut:
    vehicle = await db.get(Vehicle, session.vehicle_id)
    guest = await db.get(Guest, session.guest_id)
    out = SessionOut.model_validate(session)
    out.registration_number = vehicle.registration_number if vehicle else None
    out.guest_phone_number = guest.whatsapp_phone_number if guest else None
    return out


async def _load_session_with_access(session_id: str, current_user: User, db: AsyncSession) -> ValetSession:
    session = await session_service.get_session_or_404(db, session_id)
    await require_venue_access(session.venue_id, current_user, db)
    return session


def _require_actor_is_assigned_or_admin(session: ValetSession, current_user: User) -> None:
    if current_user.role in ADMIN_OVERRIDE_ROLES:
        return
    if current_user.role == UserRole.VALET_DESK and session.accepted_by_user_id == current_user.id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the desk person who accepted this job (or a business owner) may do this")


@router.post("/venues/{venue_id}/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    venue_id: str,
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*STAFF_ROLES)),
) -> SessionOut:
    await require_venue_access(venue_id, current_user, db)
    venue = await db.get(Venue, venue_id)
    session = await session_service.create_session(db, venue.tenant_id, venue_id, current_user, payload)
    return await _enrich(db, session)


@router.get("/venues/{venue_id}/sessions", response_model=list[SessionOut])
async def list_sessions(
    venue_id: str,
    state: SessionState | None = None,
    registration_number: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionOut]:
    await require_venue_access(venue_id, current_user, db)
    query = select(ValetSession).where(ValetSession.venue_id == venue_id)
    if state is not None:
        query = query.where(ValetSession.state == state)
    result = await db.execute(query.order_by(ValetSession.created_at.desc()))
    sessions = list(result.scalars().all())

    out = [await _enrich(db, s) for s in sessions]
    if registration_number:
        needle = session_service.normalize_registration(registration_number)
        out = [o for o in out if o.registration_number and needle in o.registration_number]
    return out


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDetailOut:
    session = await _load_session_with_access(session_id, current_user, db)
    base = await _enrich(db, session)
    events_result = await db.execute(
        select(session_service.SessionEvent)
        .where(session_service.SessionEvent.session_id == session_id)
        .order_by(session_service.SessionEvent.created_at)
    )
    events = list(events_result.scalars().all())
    return SessionDetailOut(**base.model_dump(), events=events)


@router.post("/sessions/{session_id}/accept", response_model=SessionOut)
async def accept_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.VALET_DESK)),
) -> SessionOut:
    session = await session_service.get_session_or_404(db, session_id)
    await require_venue_access(session.venue_id, current_user, db)
    updated = await session_service.accept_session(db, session_id, current_user)
    return await _enrich(db, updated)


@router.post("/sessions/{session_id}/park", response_model=SessionOut)
async def park_vehicle(
    session_id: str,
    payload: ParkInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOut:
    session = await _load_session_with_access(session_id, current_user, db)
    _require_actor_is_assigned_or_admin(session, current_user)
    updated = await session_service.transition_session(
        db, session, SessionState.PARKED, current_user, park_input=payload
    )
    return await _enrich(db, updated)


@router.post("/sessions/{session_id}/request-retrieval", response_model=SessionOut)
async def request_retrieval(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*STAFF_ROLES)),
) -> SessionOut:
    session = await _load_session_with_access(session_id, current_user, db)
    updated = await session_service.transition_session(
        db, session, SessionState.RETRIEVAL_REQUESTED, current_user, note="Guest requested retrieval (manual)"
    )
    return await _enrich(db, updated)


@router.post("/sessions/{session_id}/retrieving", response_model=SessionOut)
async def mark_retrieving(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOut:
    """Desk person has verbally dispatched a driver -- tells the guest to expect the car shortly."""
    session = await _load_session_with_access(session_id, current_user, db)
    _require_actor_is_assigned_or_admin(session, current_user)
    updated = await session_service.transition_session(db, session, SessionState.RETRIEVING, current_user)
    return await _enrich(db, updated)


@router.post("/sessions/{session_id}/ready", response_model=SessionOut)
async def mark_ready(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOut:
    session = await _load_session_with_access(session_id, current_user, db)
    _require_actor_is_assigned_or_admin(session, current_user)
    updated = await session_service.transition_session(db, session, SessionState.READY, current_user)
    return await _enrich(db, updated)


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
async def complete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionOut:
    session = await _load_session_with_access(session_id, current_user, db)
    _require_actor_is_assigned_or_admin(session, current_user)
    updated = await session_service.transition_session(db, session, SessionState.COMPLETED, current_user)
    return await _enrich(db, updated)
