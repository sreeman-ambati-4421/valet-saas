from pydantic import BaseModel

from app.models.user import UserRole


class InviteTenantAdmin(BaseModel):
    email: str
    full_name: str


class InviteVenueStaff(BaseModel):
    email: str
    full_name: str
    role: UserRole  # validated further in the router to exclude admin roles


class InviteOut(BaseModel):
    user_id: str
    email: str
    role: UserRole
    message: str
