import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class SessionState(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    PARKED = "PARKED"
    RETRIEVAL_REQUESTED = "RETRIEVAL_REQUESTED"
    RETRIEVING = "RETRIEVING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Explicit allowed transitions — the state machine's single source of truth.
# Enforced in the session service layer, not just documented here.
#
# There is no separate driver login: a valet_desk person accepts the guest's
# WhatsApp request, verbally dispatches a driver, and reports outcomes back
# (dispatch is never itself a tracked state -- only its before/after are).
ALLOWED_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.REQUESTED: {SessionState.ACCEPTED, SessionState.CANCELLED},
    SessionState.ACCEPTED: {SessionState.PARKED, SessionState.CANCELLED},
    SessionState.PARKED: {SessionState.RETRIEVAL_REQUESTED, SessionState.CANCELLED},
    SessionState.RETRIEVAL_REQUESTED: {SessionState.RETRIEVING, SessionState.CANCELLED},
    SessionState.RETRIEVING: {SessionState.READY, SessionState.CANCELLED},
    SessionState.READY: {SessionState.COMPLETED},
    SessionState.COMPLETED: set(),
    SessionState.CANCELLED: set(),
}


class ValetSession(Base, UUIDPk, TimestampMixin):
    __tablename__ = "valet_sessions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    guest_id: Mapped[str] = mapped_column(ForeignKey("guests.id"), index=True)
    # Null until parked: the registration number is now captured from the
    # driver at the Mark Parked step, not from the guest at request time.
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True, index=True)
    # The physical key tag attached to this vehicle for the session's
    # duration -- set at creation (scanned by the guest, or auto-assigned
    # for a staff-created session), released back to AVAILABLE on
    # completion/cancellation.
    qr_code_id: Mapped[str | None] = mapped_column(ForeignKey("qr_codes.id"), nullable=True)

    accepted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    state: Mapped[SessionState] = mapped_column(
        Enum(SessionState, native_enum=False, length=32), default=SessionState.REQUESTED, index=True
    )

    # True only for sessions created by the guest scanning a QR code and
    # messaging WhatsApp directly. For these, retrieval can only be
    # requested by the guest's own WhatsApp message (the "car" keyword) --
    # never manually by staff. Staff-created sessions (for guests without
    # WhatsApp) keep the manual request-retrieval fallback.
    created_via_whatsapp: Mapped[bool] = mapped_column(default=False)

    events: Mapped[list["SessionEvent"]] = relationship(back_populates="session", order_by="SessionEvent.created_at")


class SessionEvent(Base, UUIDPk, TimestampMixin):
    __tablename__ = "session_events"

    session_id: Mapped[str] = mapped_column(ForeignKey("valet_sessions.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["ValetSession"] = relationship(back_populates="events")
