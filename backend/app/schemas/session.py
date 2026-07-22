from datetime import datetime

from pydantic import BaseModel

from app.models.session import SessionState


class SessionCreate(BaseModel):
    guest_phone_number: str
    guest_name: str | None = None
    # The specific physical tag the guest scanned. Omitted for a
    # staff-created session (guest without WhatsApp) -- the backend
    # auto-assigns any available tag for the venue in that case.
    qr_code_id: str | None = None


class ParkInput(BaseModel):
    registration_number: str


class SessionEventOut(BaseModel):
    id: str
    actor_user_id: str | None
    from_state: str | None
    to_state: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    tenant_id: str
    venue_id: str
    guest_id: str
    vehicle_id: str | None
    qr_code_id: str | None
    accepted_by_user_id: str | None
    created_via_whatsapp: bool
    state: SessionState
    created_at: datetime
    updated_at: datetime
    registration_number: str | None = None
    guest_phone_number: str | None = None
    tag_label: str | None = None

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    events: list[SessionEventOut] = []
