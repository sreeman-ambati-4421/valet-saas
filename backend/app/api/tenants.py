from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import require_role
from app.models.tenant import Tenant
from app.models.user import UserRole
from app.schemas.tenant import TenantCreate, TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(UserRole.SAAS_OWNER)),
) -> Tenant:
    tenant = Tenant(name=payload.name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(UserRole.SAAS_OWNER)),
) -> list[Tenant]:
    result = await db.execute(select(Tenant))
    return list(result.scalars().all())
