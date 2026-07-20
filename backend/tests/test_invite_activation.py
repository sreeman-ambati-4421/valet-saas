from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user


async def test_inactive_user_is_rejected_by_normal_endpoints(client, db):
    tenant = await make_tenant(db)
    user = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant, is_active=False)

    resp = await client.get("/me", headers=auth_header(user))

    assert resp.status_code == 401


async def test_confirm_activates_an_inactive_user(client, db):
    tenant = await make_tenant(db)
    user = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant, is_active=False)

    confirm_resp = await client.post("/me/confirm", headers=auth_header(user))
    assert confirm_resp.status_code == 204

    me_resp = await client.get("/me", headers=auth_header(user))
    assert me_resp.status_code == 200

    await db.refresh(user)
    assert user.is_active is True


async def test_confirm_is_idempotent_for_already_active_user(client, db):
    tenant = await make_tenant(db)
    user = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant, is_active=True)

    resp = await client.post("/me/confirm", headers=auth_header(user))

    assert resp.status_code == 204


async def test_confirm_requires_a_valid_token_even_if_inactive(client):
    resp = await client.post("/me/confirm")

    assert resp.status_code == 401
