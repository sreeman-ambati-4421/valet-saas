from pydantic import BaseModel


class QRCodeCreate(BaseModel):
    label: str | None = None


class QRCodeOut(BaseModel):
    id: str
    venue_id: str
    token: str
    label: str | None
    is_active: bool
    wa_link: str = ""

    model_config = {"from_attributes": True}
