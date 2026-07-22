import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class TagStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"


class QRCode(Base, UUIDPk, TimestampMixin):
    """A physical, reusable key tag: printed with this QR + its label (e.g.
    "Tag 007"), attached to a vehicle's keys for the duration of one valet
    session, then released back to the available pool on completion."""

    __tablename__ = "qr_codes"

    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "Tag 007"
    is_active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[TagStatus] = mapped_column(
        Enum(TagStatus, native_enum=False, length=16, values_callable=lambda obj: [e.value for e in obj]),
        default=TagStatus.AVAILABLE,
    )
