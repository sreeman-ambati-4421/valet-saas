from pydantic import BaseModel, Field


class AcceptInvite(BaseModel):
    token: str
    password: str = Field(min_length=8)
