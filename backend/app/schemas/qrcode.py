from pydantic import BaseModel, Field

from app.models.parking import TagStatus


class QRCodeCreate(BaseModel):
    count: int = Field(default=1, ge=1, le=100)


class QRCodeOut(BaseModel):
    id: str
    venue_id: str
    token: str
    label: str | None
    is_active: bool
    status: TagStatus
    wa_link: str = ""

    model_config = {"from_attributes": True}
