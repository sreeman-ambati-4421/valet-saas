from unittest.mock import patch

from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


def _mock_generate_link(email, redirect_to):
    return f"supabase-uid-for-{email}", f"https://example.supabase.co/verify?token=fake-for-{email}"


async def test_tenant_admin_invites_venue_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ) as mock_send:
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "valet1@example.com", "full_name": "V One", "phone_number": "+911111111111", "role": "valet"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "valet1@example.com"
    assert body["role"] == "valet"
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "+911111111111"
    # Sent as our own click-through page (defeats WhatsApp's link-preview
    # pre-fetch consuming the single-use token), with the real link embedded.
    sent_message = mock_send.call_args[0][1]
    assert "/invite-redirect?to=" in sent_message
    assert "example.supabase.co" in sent_message

    # confirm the created user actually has venue access and correct tenant
    me_resp = await client.get(f"/venues/{venue.id}", headers=auth_header(admin))
    assert me_resp.status_code == 200


async def test_tenant_admin_cannot_invite_staff_into_other_tenants_venue(client, db):
    tenant_a = await make_tenant(db, "A")
    tenant_b = await make_tenant(db, "B")
    venue_b = await make_venue(db, tenant_b)
    admin_a = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant_a)

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ):
        resp = await client.post(
            f"/venues/{venue_b.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "phone_number": "+911111111111", "role": "valet"},
            headers=auth_header(admin_a),
        )

    assert resp.status_code == 404


async def test_non_admin_cannot_invite_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    valet = await make_user(db, UserRole.VALET, tenant=tenant, venues=[venue])

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "phone_number": "+911111111111", "role": "valet"},
            headers=auth_header(valet),
        )

    assert resp.status_code == 403


async def test_cannot_invite_admin_role_via_venue_staff_endpoint(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "x@example.com", "full_name": "X", "phone_number": "+911111111111", "role": "tenant_admin"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 400


async def test_platform_admin_invites_tenant_admin(client, db):
    tenant = await make_tenant(db)
    platform_admin = await make_user(db, UserRole.PLATFORM_SUPER_ADMIN, tenant=None)

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ) as mock_send:
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"email": "admin2@example.com", "full_name": "Admin Two", "phone_number": "+912222222222"},
            headers=auth_header(platform_admin),
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "tenant_admin"
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "+912222222222"


async def test_tenant_admin_cannot_invite_other_tenant_admins(client, db):
    tenant = await make_tenant(db)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ):
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"email": "x@example.com", "full_name": "X", "phone_number": "+911111111111"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 403


async def test_duplicate_invite_surfaces_clean_error_not_500(client, db):
    from app.core.supabase_admin import StaffInviteError

    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)

    with patch(
        "app.core.supabase_admin.create_invite_link", side_effect=StaffInviteError("Email already registered")
    ), patch("app.core.twilio_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"email": "dupe@example.com", "full_name": "Dupe", "phone_number": "+911111111111", "role": "valet"},
            headers=auth_header(admin),
        )

    assert resp.status_code == 422
    assert "already registered" in resp.json()["detail"]
    mock_send.assert_not_called()


async def test_resubmitting_same_email_fails_clean_not_500(client, db):
    # Reproduces a real production crash: submitting the same invite twice
    # (e.g. a double-click) previously hit an unhandled DB unique-constraint
    # error on the second attempt instead of a clean 4xx.
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    admin = await make_user(db, UserRole.TENANT_ADMIN, tenant=tenant)
    payload = {"email": "resend@example.com", "full_name": "Re Send", "phone_number": "+911111111111", "role": "valet"}

    with patch("app.core.supabase_admin.create_invite_link", side_effect=_mock_generate_link), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ):
        first = await client.post(f"/venues/{venue.id}/staff", json=payload, headers=auth_header(admin))
        second = await client.post(f"/venues/{venue.id}/staff", json=payload, headers=auth_header(admin))

    assert first.status_code == 201
    assert second.status_code == 422
    assert "already invited or registered" in second.json()["detail"]
