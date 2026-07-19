import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class SessionState(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    VEHICLE_COLLECTED = "VEHICLE_COLLECTED"
    PARKED = "PARKED"
    RETRIEVAL_REQUESTED = "RETRIEVAL_REQUESTED"
    RETRIEVING = "RETRIEVING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Explicit allowed transitions — the state machine's single source of truth.
# Enforced in the session service layer, not just documented here.
ALLOWED_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.REQUESTED: {SessionState.ASSIGNED, SessionState.CANCELLED},
    SessionState.ASSIGNED: {SessionState.VEHICLE_COLLECTED, SessionState.CANCELLED},
    SessionState.VEHICLE_COLLECTED: {SessionState.PARKED, SessionState.CANCELLED},
    SessionState.PARKED: {SessionState.RETRIEVAL_REQUESTED, SessionState.CANCELLED},
    SessionState.RETRIEVAL_REQUESTED: {SessionState.RETRIEVING, SessionState.CANCELLED},
    SessionState.RETRIEVING: {SessionState.READY, SessionState.CANCELLED},
    SessionState.READY: {SessionState.DELIVERED},
    SessionState.DELIVERED: {SessionState.COMPLETED},
    SessionState.COMPLETED: set(),
    SessionState.CANCELLED: set(),
}


class ValetSession(Base, UUIDPk, TimestampMixin):
    __tablename__ = "valet_sessions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    guest_id: Mapped[str] = mapped_column(ForeignKey("guests.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), index=True)
    qr_code_id: Mapped[str | None] = mapped_column(ForeignKey("qr_codes.id"), nullable=True)

    assigned_valet_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    state: Mapped[SessionState] = mapped_column(
        Enum(SessionState, native_enum=False, length=32), default=SessionState.REQUESTED, index=True
    )

    parking_zone_id: Mapped[str | None] = mapped_column(ForeignKey("parking_zones.id"), nullable=True)
    parking_slot_id: Mapped[str | None] = mapped_column(ForeignKey("parking_slots.id"), nullable=True)
    key_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)

    events: Mapped[list["SessionEvent"]] = relationship(back_populates="session", order_by="SessionEvent.created_at")


class SessionEvent(Base, UUIDPk, TimestampMixin):
    __tablename__ = "session_events"

    session_id: Mapped[str] = mapped_column(ForeignKey("valet_sessions.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["ValetSession"] = relationship(back_populates="events")
