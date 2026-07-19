from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import get_current_user, require_role, require_venue_access
from app.models.tenant import Venue
from app.models.user import User, UserRole
from app.schemas.tenant import VenueCreate, VenueOut

router = APIRouter(prefix="/venues", tags=["venues"])


@router.post("", response_model=VenueOut, status_code=201)
async def create_venue(
    payload: VenueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN)),
) -> Venue:
    # tenant_id is always the caller's own tenant -- VenueCreate has no tenant_id
    # field at all, so there is nothing in the request body that could override it.
    venue = Venue(tenant_id=current_user.tenant_id, name=payload.name, address=payload.address, timezone=payload.timezone)
    db.add(venue)
    await db.commit()
    await db.refresh(venue)
    return venue


@router.get("/{venue_id}", response_model=VenueOut)
async def get_venue(
    venue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Venue:
    await require_venue_access(venue_id, current_user, db)
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    return result.scalar_one()
