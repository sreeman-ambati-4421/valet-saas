from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class Guest(Base, UUIDPk, TimestampMixin):
    __tablename__ = "guests"

    # Guests are global, not tenant-scoped: the same person may valet
    # their car at multiple unrelated venues over time.
    whatsapp_phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Vehicle(Base, UUIDPk, TimestampMixin):
    __tablename__ = "vehicles"

    # Normalized (uppercased, whitespace-stripped) registration number.
    registration_number: Mapped[str] = mapped_column(String(32), index=True)
