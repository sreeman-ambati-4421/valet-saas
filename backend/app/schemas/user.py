from pydantic import BaseModel

from app.models.user import UserRole


class VenueSummary(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    tenant_id: str | None
    venues: list[VenueSummary]
