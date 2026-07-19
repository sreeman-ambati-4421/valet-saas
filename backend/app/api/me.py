from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import get_current_user
from app.models.tenant import Venue
from app.models.user import User, UserRole, UserVenueAccess
from app.schemas.user import MeOut, VenueSummary

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def read_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    venues: list[Venue] = []

    if current_user.role in (UserRole.TENANT_ADMIN,):
        result = await db.execute(select(Venue).where(Venue.tenant_id == current_user.tenant_id))
        venues = list(result.scalars().all())
    elif current_user.role in (UserRole.VENUE_MANAGER, UserRole.VALET):
        result = await db.execute(
            select(Venue).join(UserVenueAccess, UserVenueAccess.venue_id == Venue.id).where(
                UserVenueAccess.user_id == current_user.id
            )
        )
        venues = list(result.scalars().all())
    # platform_super_admin: not scoped to any venue list here.

    return MeOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        venues=[VenueSummary.model_validate(v) for v in venues],
    )
