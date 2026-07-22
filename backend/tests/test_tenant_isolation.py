from app.models.user import UserRole
from tests.conftest import auth_header, make_qr_code, make_tenant, make_user, make_venue


async def test_business_owner_cannot_read_other_tenants_venue(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    tenant_b = await make_tenant(db, "Tenant B")
    venue_b = await make_venue(db, tenant_b, "B's Venue")
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a)

    resp = await client.get(f"/venues/{venue_b.id}", headers=auth_header(owner_a))

    assert resp.status_code == 404


async def test_business_owner_cannot_create_venue_under_own_role_but_wrong_id_hack(client, db):
    # VenueCreate has no tenant_id field at all -- confirm the created venue
    # always lands under the caller's own tenant regardless of any attempt
    # to smuggle a different tenant id in the request body.
    tenant_a = await make_tenant(db, "Tenant A")
    tenant_b = await make_tenant(db, "Tenant B")
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a)

    resp = await client.post(
        "/venues",
        json={"name": "Sneaky Venue", "tenant_id": tenant_b.id},
        headers=auth_header(owner_a),
    )

    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == tenant_a.id


async def test_business_owner_cannot_act_on_other_tenants_venue_sessions(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    tenant_b = await make_tenant(db, "Tenant B")
    venue_b = await make_venue(db, tenant_b, "B's Venue")
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a, venues=[])

    resp = await client.post(
        f"/venues/{venue_b.id}/sessions",
        json={"guest_phone_number": "+919999999999"},
        headers=auth_header(owner_a),
    )

    assert resp.status_code == 404


async def test_desk_person_without_venue_access_is_forbidden_even_within_same_tenant(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    venue_1 = await make_venue(db, tenant_a, "Venue 1")
    venue_2 = await make_venue(db, tenant_a, "Venue 2")
    # Desk person only has access to venue_1, not venue_2, despite same tenant.
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant_a, venues=[venue_1])

    resp = await client.get(f"/venues/{venue_2.id}/sessions", headers=auth_header(desk))

    assert resp.status_code == 403


async def test_session_created_at_tenant_a_is_invisible_to_tenant_b_owner(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    tenant_b = await make_tenant(db, "Tenant B")
    venue_a = await make_venue(db, tenant_a, "Venue A")
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a, venues=[venue_a])
    owner_b = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_b)
    await make_qr_code(db, venue_a)

    create_resp = await client.post(
        f"/venues/{venue_a.id}/sessions",
        json={"guest_phone_number": "+919999999999"},
        headers=auth_header(owner_a),
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    resp = await client.get(f"/sessions/{session_id}", headers=auth_header(owner_b))

    assert resp.status_code == 404


async def test_saas_owner_can_access_any_tenant(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    venue_a = await make_venue(db, tenant_a, "Venue A")
    saas_owner = await make_user(db, UserRole.SAAS_OWNER, tenant=None)

    resp = await client.get(f"/venues/{venue_a.id}", headers=auth_header(saas_owner))

    assert resp.status_code == 200


async def test_non_saas_owner_cannot_list_tenants(client, db):
    tenant_a = await make_tenant(db, "Tenant A")
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a)

    resp = await client.get("/tenants", headers=auth_header(owner_a))

    assert resp.status_code == 403


async def test_no_token_is_rejected():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/me")

    assert resp.status_code == 401
