from pydantic import BaseModel

from app.models.user import UserRole


class InviteBusinessOwner(BaseModel):
    phone_number: str  # WhatsApp number they'll log in with
    full_name: str


class InviteVenueStaff(BaseModel):
    # No role field: valet_desk is the only invitable venue-level role.
    phone_number: str
    full_name: str


class InviteOut(BaseModel):
    user_id: str
    phone_number: str
    role: UserRole
    message: str
