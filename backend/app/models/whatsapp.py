from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPk


class WhatsAppAccount(Base, UUIDPk, TimestampMixin):
    __tablename__ = "whatsapp_accounts"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    # Twilio identifiers only — actual auth token lives in a secret manager, never this table.
    twilio_whatsapp_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    twilio_account_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)


class Subscription(Base, UUIDPk, TimestampMixin):
    __tablename__ = "subscriptions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    plan: Mapped[str] = mapped_column(String(32), default="pilot")
    status: Mapped[str] = mapped_column(String(32), default="active")
    venue_count: Mapped[int] = mapped_column(default=1)
