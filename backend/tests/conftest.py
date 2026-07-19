import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app
from app.models.tenant import Tenant, Venue
from app.models.user import User, UserRole, UserVenueAccess

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def make_token(user: User) -> str:
    return jwt.encode(
        {"sub": user.supabase_user_id, "aud": "authenticated", "email": user.email},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


def auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {make_token(user)}"}


async def make_user(
    db,
    role: UserRole,
    tenant: Tenant | None = None,
    venues: list[Venue] | None = None,
    email: str | None = None,
) -> User:
    user = User(
        supabase_user_id=str(uuid.uuid4()),
        tenant_id=tenant.id if tenant else None,
        email=email or f"{uuid.uuid4()}@example.com",
        full_name="Test User",
        role=role,
    )
    db.add(user)
    await db.flush()
    for v in venues or []:
        db.add(UserVenueAccess(user_id=user.id, venue_id=v.id))
    await db.commit()
    await db.refresh(user)
    return user


async def make_tenant(db, name: str = "Test Tenant") -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def make_venue(db, tenant: Tenant, name: str = "Test Venue") -> Venue:
    venue = Venue(tenant_id=tenant.id, name=name)
    db.add(venue)
    await db.commit()
    await db.refresh(venue)
    return venue
