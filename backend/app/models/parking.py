from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class ParkingZone(Base, UUIDPk, TimestampMixin):
    __tablename__ = "parking_zones"

    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))


class ParkingSlot(Base, UUIDPk, TimestampMixin):
    __tablename__ = "parking_slots"

    zone_id: Mapped[str] = mapped_column(ForeignKey("parking_zones.id"), index=True)
    label: Mapped[str] = mapped_column(String(64))
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False)


class QRCode(Base, UUIDPk, TimestampMixin):
    __tablename__ = "qr_codes"

    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "Main Entrance"
    is_active: Mapped[bool] = mapped_column(default=True)
