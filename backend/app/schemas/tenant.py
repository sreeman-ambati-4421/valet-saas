from datetime import datetime

from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VenueCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "UTC"


class VenueOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    address: str | None
    timezone: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
