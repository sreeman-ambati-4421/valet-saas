from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class Guest(Base, UUIDPk, TimestampMixin):
    __tablename__ = "guests"

    # Guests are global, not tenant-scoped: the same person may valet
    # their car at multiple unrelated venues over time.
    whatsapp_phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scratch state for the QR-scan -> reg-number handshake over WhatsApp:
    # set when a guest scans a QR and we're waiting for their reg number
    # reply, cleared once the session is created.
    pending_venue_id: Mapped[str | None] = mapped_column(ForeignKey("venues.id"), nullable=True)


class Vehicle(Base, UUIDPk, TimestampMixin):
    __tablename__ = "vehicles"

    # Normalized (uppercased, whitespace-stripped) registration number.
    registration_number: Mapped[str] = mapped_column(String(32), index=True)
    make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
