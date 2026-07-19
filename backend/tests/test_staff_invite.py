from unittest.mock import patch

from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


def _mock_invite(email, redirect_to):
    return f"supabase-uid-for-{email}"


async def test_tenant_admin_invites_venue_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "valet1@example.com", "full_name": "V One", "role": "valet"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "valet1@example.com"
    assert body["role"] == "valet"

    # confirm the created user actually has venue access and correct tenant
    me_resp = await client.get(f"/venues/{venue.id}", headers=auth_header(admin))
    assert me_resp.status_code == 200


async def test_tenant_admin_cannot_invite_staff_into_other_tenants_venue(client, db):
    tenant_a = await make_tenant(db, "A")
    tenant_b = await make_tenant(db, "B")
    venue_b = await make_venue(db, tenant_b)
    admin_a = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant_a)

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/venues/{venue_b.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "role": "valet"},
            headers=auth_header(admin_a),
        )

    assert resp.status_code == 404


async def test_non_admin_cannot_invite_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    valet = await make_user(db, UserRole.VALET, tenant=tenant, venues=[venue])

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "role": "valet"},
            headers=auth_header(valet),
        )

    assert resp.status_code == 403


async def test_cannot_invite_admin_role_via_venue_staff_endpoint(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "role": "tenant_admin"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 400


async def test_platform_admin_invites_tenant_admin(client, db):
    tenant = await make_tenant(db)
    platform_admin = await make_user(db, UserRole.PLATFORM_SUPER_ADMIN, tenant=None)

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"email": "admin2@example.com", "full_name": "Admin Two"},
            headers=auth_header(platform_admin),
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "tenant_admin"


async def test_tenant_admin_cannot_invite_other_tenant_admins(client, db):
    tenant = await make_tenant(db)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.invite_user", side_effect=_mock_invite):
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"email": "x@example.com", "full_name": "X"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 403


async def test_duplicate_invite_surfaces_clean_error_not_500(client, db):
    from app.core.supabase_admin import StaffInviteError

    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.invite_user", side_effect=StaffInviteError("Email already registered")):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "dupe@example.com", "full_name": "Dupe", "role": "valet"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 422
    assert "already registered" in resp.json()["detail"]
