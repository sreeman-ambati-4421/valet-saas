from datetime import datetime

from pydantic import BaseModel

from app.models.session import SessionState


class SessionCreate(BaseModel):
    registration_number: str
    guest_phone_number: str
    guest_name: str | None = None


class ParkInput(BaseModel):
    parking_zone_id: str | None = None
    parking_slot_id: str | None = None
    key_tag: str


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
    vehicle_id: str
    assigned_valet_id: str | None
    state: SessionState
    parking_zone_id: str | None
    parking_slot_id: str | None
    key_tag: str | None
    created_at: datetime
    updated_at: datetime
    registration_number: str | None = None
    guest_phone_number: str | None = None

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    events: list[SessionEventOut] = []
