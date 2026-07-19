from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.supabase_admin import StaffInviteError
from app.deps import require_role, require_venue_access
from app.models.tenant import Tenant, Venue
from app.models.user import User, UserRole
from app.schemas.staff import InviteOut, InviteTenantAdmin, InviteVenueStaff
from app.services.staff_service import create_invited_user

router = APIRouter(tags=["staff"])


@router.post("/tenants/{tenant_id}/admins", response_model=InviteOut, status_code=201)
async def invite_tenant_admin(
    tenant_id: str,
    payload: InviteTenantAdmin,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.PLATFORM_SUPER_ADMIN)),
) -> InviteOut:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    try:
        user = await create_invited_user(
            db, payload.email, payload.full_name, payload.phone_number, UserRole.TENANT_ADMIN, tenant_id=tenant_id
        )
    except StaffInviteError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None

    return InviteOut(
        user_id=user.id, email=user.email, role=user.role, message=f"Invite sent via WhatsApp to {payload.phone_number}"
    )


@router.post("/venues/{venue_id}/staff", response_model=InviteOut, status_code=201)
async def invite_venue_staff(
    venue_id: str,
    payload: InviteVenueStaff,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.PLATFORM_SUPER_ADMIN)),
) -> InviteOut:
    if payload.role not in (UserRole.VENUE_MANAGER, UserRole.VALET):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be venue_manager or valet")

    await require_venue_access(venue_id, current_user, db)
    venue = await db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")

    try:
        user = await create_invited_user(
            db,
            payload.email,
            payload.full_name,
            payload.phone_number,
            payload.role,
            tenant_id=venue.tenant_id,
            venue_id=venue_id,
        )
    except StaffInviteError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None

    return InviteOut(
        user_id=user.id, email=user.email, role=user.role, message=f"Invite sent via WhatsApp to {payload.phone_number}"
    )
