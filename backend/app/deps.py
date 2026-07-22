from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_supabase_jwt
from app.models.user import User, UserRole, UserVenueAccess

bearer_scheme = HTTPBearer(auto_error=False)


async def _resolve_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        payload = decode_supabase_jwt(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from None

    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject claim")

    result = await db.execute(select(User).where(User.supabase_user_id == supabase_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No account for this token")

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _resolve_user_from_token(credentials, db)
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No active account for this token")
    return user


def require_role(*allowed_roles: UserRole):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{current_user.role.value}' is not permitted to perform this action",
            )
        return current_user

    return _check


async def require_venue_access(venue_id: str, current_user: User, db: AsyncSession) -> None:
    """Confirms current_user may act on venue_id. Raises 403/404 otherwise.

    Tenant/venue scoping is always resolved server-side from the authenticated
    user's own membership -- never from a client-supplied tenant/venue id alone.
    """
    from app.models.tenant import Venue  # local import avoids a circular import at module load

    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    venue = result.scalar_one_or_none()
    if venue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")

    if current_user.role == UserRole.SAAS_OWNER:
        return

    if venue.tenant_id != current_user.tenant_id:
        # Deliberately 404, not 403: don't reveal that a venue with this id
        # exists in another tenant at all.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venue not found")

    if current_user.role == UserRole.BUSINESS_OWNER:
        return

    access = await db.execute(
        select(UserVenueAccess).where(
            UserVenueAccess.user_id == current_user.id,
            UserVenueAccess.venue_id == venue_id,
        )
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not assigned to this venue")
