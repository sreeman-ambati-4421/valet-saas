from unittest.mock import patch

from sqlalchemy import select

from app.core.security import create_invite_token
from app.models.user import User, UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


def _mock_create_phone_confirmed_user(phone_number, full_name):
    return f"supabase-uid-for-{phone_number}"


async def _invite_desk_staff(client, db, phone_number="+915555555555"):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    with patch(
        "app.core.supabase_admin.create_phone_confirmed_user", side_effect=_mock_create_phone_confirmed_user
    ), patch("app.core.twilio_client.send_whatsapp_text"):
        resp = await client.post(
            f"/venues/{venue.id}/staff",
            json={"phone_number": phone_number, "full_name": "Desk One"},
            headers=auth_header(owner),
        )
    assert resp.status_code == 201, resp.text

    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one()


async def test_accept_invite_with_valid_token_sets_password_and_activates(client, db):
    user = await _invite_desk_staff(client, db)
    assert user.is_active is False
    token = create_invite_token(user.id)

    with patch("app.core.supabase_admin.set_user_password") as mock_set_password:
        resp = await client.post("/invites/accept", json={"token": token, "password": "supersecret1"})

    assert resp.status_code == 204, resp.text
    mock_set_password.assert_called_once_with(user.supabase_user_id, "supersecret1")

    await db.refresh(user)
    assert user.is_active is True


async def test_accept_invite_with_invalid_token_is_rejected(client, db):
    resp = await client.post("/invites/accept", json={"token": "not-a-real-token", "password": "supersecret1"})

    assert resp.status_code == 400


async def test_accept_invite_twice_is_rejected(client, db):
    user = await _invite_desk_staff(client, db, phone_number="+916666666666")
    token = create_invite_token(user.id)

    with patch("app.core.supabase_admin.set_user_password"):
        first = await client.post("/invites/accept", json={"token": token, "password": "supersecret1"})
        second = await client.post("/invites/accept", json={"token": token, "password": "differentpass1"})

    assert first.status_code == 204
    assert second.status_code == 409


async def test_accept_invite_rejects_short_password(client, db):
    user = await _invite_desk_staff(client, db, phone_number="+917777777777")
    token = create_invite_token(user.id)

    resp = await client.post("/invites/accept", json={"token": token, "password": "short"})

    assert resp.status_code == 422
