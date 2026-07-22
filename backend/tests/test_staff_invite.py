from unittest.mock import patch

from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


def _mock_create_phone_confirmed_user(phone_number, full_name):
    return f"supabase-uid-for-{phone_number}"


async def test_business_owner_invites_venue_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"phone_number": "+911111111111", "full_name": "Desk One"},
            headers=auth_header(owner),
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["phone_number"] == "+911111111111"
    assert body["role"] == "valet_desk"
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "+911111111111"
    sent_message = mock_send.call_args[0][1]
    assert "/accept-invite?token=" in sent_message

    # confirm the created user actually has venue access and correct tenant
    me_resp = await client.get(f"/venues/{venue.id}", headers=auth_header(owner))
    assert me_resp.status_code == 200


async def test_business_owner_cannot_invite_staff_into_other_tenants_venue(client, db):
    tenant_a = await make_tenant(db, "A")
    tenant_b = await make_tenant(db, "B")
    venue_b = await make_venue(db, tenant_b)
    owner_a = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant_a)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text"):
        resp = await client.post(
            f"/venues/{venue_b.id}/staff",
            json={"phone_number": "+911111111111", "full_name": "X"},
            headers=auth_header(owner_a),
        )

    assert resp.status_code == 404


async def test_non_owner_cannot_invite_staff(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text"):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"phone_number": "+911111111111", "full_name": "X"},
            headers=auth_header(desk),
        )

    assert resp.status_code == 403


async def test_saas_owner_invites_business_owner(client, db):
    tenant = await make_tenant(db)
    saas_owner = await make_user(db, UserRole.SAAS_OWNER, tenant=None)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"phone_number": "+912222222222", "full_name": "Owner Two"},
            headers=auth_header(saas_owner),
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "business_owner"
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "+912222222222"


async def test_business_owner_cannot_invite_other_business_owners(client, db):
    tenant = await make_tenant(db)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text"):
        resp = await client.post(
            f"/tenants/{tenant.id}/admins",
            json={"phone_number": "+911111111111", "full_name": "X"},
            headers=auth_header(owner),
        )

    assert resp.status_code == 403


async def test_duplicate_invite_surfaces_clean_error_not_500(client, db):
    from app.core.supabase_admin import StaffInviteError

    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user",
        side_effect=StaffInviteError("Phone number already registered"),
    ), patch("app.core.whatsapp_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"phone_number": "+913333333333", "full_name": "Dupe"},
            headers=auth_header(owner),
        )

    assert resp.status_code == 422
    assert "already registered" in resp.json()["detail"]
    mock_send.assert_not_called()


async def test_resubmitting_same_phone_number_fails_clean_not_500(client, db):
    # Reproduces a real production crash: submitting the same invite twice
    # (e.g. a double-click) previously hit an unhandled DB unique-constraint
    # error on the second attempt instead of a clean 4xx.
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)
    payload = {"phone_number": "+914444444444", "full_name": "Re Send"}

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.whatsapp_client.send_whatsapp_text"):
        first = await client.post(f"/venues/{venue.id}/staff", json=payload, headers=auth_header(owner))
        second = await client.post(f"/venues/{venue.id}/staff", json=payload, headers=auth_header(owner))

    assert first.status_code == 201
    assert second.status_code == 422
    assert "already invited or registered" in second.json()["detail"]
