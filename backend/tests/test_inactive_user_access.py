from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user


async def test_inactive_user_is_rejected_by_normal_endpoints(client, db):
    tenant = await make_tenant(db)
    user = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, is_active=False)

    resp = await client.get("/me", headers=auth_header(user))

    assert resp.status_code == 401


async def test_active_user_can_use_normal_endpoints(client, db):
    tenant = await make_tenant(db)
    user = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, is_active=True)

    resp = await client.get("/me", headers=auth_header(user))

    assert resp.status_code == 200
