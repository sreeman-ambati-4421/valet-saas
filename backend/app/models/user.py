import enum

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class UserRole(str, enum.Enum):
    PLATFORM_SUPER_ADMIN = "platform_super_admin"
    TENANT_ADMIN = "tenant_admin"
    VENUE_MANAGER = "venue_manager"
    VALET = "valet"


class User(Base, UUIDPk, TimestampMixin):
    __tablename__ = "users"

    # Maps 1:1 to the Supabase Auth user id (auth.users.id). Not a foreign key
    # since Supabase Auth lives in a separate schema managed by Supabase itself.
    supabase_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Null only for platform_super_admin, who is not scoped to any single tenant.
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    # values_callable persists the lowercase .value ("platform_super_admin")
    # rather than SQLAlchemy's default of the uppercase member .name
    # ("PLATFORM_SUPER_ADMIN") -- keeps the DB representation consistent with
    # what the API/frontend use everywhere else.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32, values_callable=lambda obj: [e.value for e in obj])
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    venue_access: Mapped[list["UserVenueAccess"]] = relationship(back_populates="user")


class UserVenueAccess(Base, UUIDPk, TimestampMixin):
    __tablename__ = "user_venue_access"
    __table_args__ = (UniqueConstraint("user_id", "venue_id", name="uq_user_venue"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)

    user: Mapped["User"] = relationship(back_populates="venue_access")
