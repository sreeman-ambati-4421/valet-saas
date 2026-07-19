from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class Tenant(Base, UUIDPk, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

    venues: Mapped[list["Venue"]] = relationship(back_populates="tenant")


class Venue(Base, UUIDPk, TimestampMixin):
    __tablename__ = "venues"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    is_active: Mapped[bool] = mapped_column(default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="venues")
