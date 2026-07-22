from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import supabase_admin
from app.core.db import get_db
from app.core.security import InvalidTokenError, verify_invite_token
from app.core.supabase_admin import StaffInviteError
from app.models.user import User
from app.schemas.invite import AcceptInvite

router = APIRouter(tags=["invites"])


@router.post("/invites/accept", status_code=204)
async def accept_invite(
    payload: AcceptInvite,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Called from the accept-invite page, before the recipient has any
    session at all -- authorization here comes entirely from possessing a
    valid, unexpired invite token, the same trust model a clickable invite
    link always has.
    """
    try:
        user_id = verify_invite_token(payload.token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invite link is invalid or has expired.") from None

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invite link is invalid or has expired.")

    if user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "This invite has already been accepted.")

    try:
        supabase_admin.set_user_password(user.supabase_user_id, payload.password)
    except StaffInviteError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None

    user.is_active = True
    await db.commit()
