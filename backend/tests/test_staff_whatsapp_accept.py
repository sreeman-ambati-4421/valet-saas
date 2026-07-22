from unittest.mock import patch

from app.services import session_service
from app.models.session import SessionState, ValetSession
from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue

DESK_PHONE = "+919000000001"
OWNER_PHONE = "+919000000002"


async def _post_webhook(client, from_phone: str, body: str):
    with patch("app.core.twilio_client.verify_webhook_signature", return_value=True), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ) as mock_send:
        resp = await client.post(
            "/webhooks/twilio/whatsapp",
            data={"From": f"whatsapp:{from_phone}", "Body": body},
            headers={"X-Twilio-Signature": "fake"},
        )
    return resp, mock_send


async def _create_session(client, owner, venue, reg="XY1234", guest_phone="+911111111111"):
    resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": reg, "guest_phone_number": guest_phone},
        headers=auth_header(owner),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_new_session_notifies_desk_staff_with_access(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, phone_number=OWNER_PHONE)
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue], phone_number=DESK_PHONE)

    with patch("app.core.twilio_client.send_whatsapp_text") as mock_send:
        session = await _create_session(client, owner, venue)

    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == desk.phone_number
    message = mock_send.call_args[0][1]
    assert "XY1234" in message
    assert f"ACCEPT-{session_service.short_code(session['id'])}" in message


async def test_valet_desk_accepts_via_whatsapp_reply(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, phone_number=OWNER_PHONE)
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue], phone_number=DESK_PHONE)

    with patch("app.core.twilio_client.send_whatsapp_text"):
        session = await _create_session(client, owner, venue)

    code = session_service.short_code(session["id"])
    resp, mock_send = await _post_webhook(client, DESK_PHONE, f"ACCEPT-{code}")

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "XY1234" in mock_send.call_args[0][1]

    updated = await db.get(ValetSession, session["id"])
    assert updated.state == SessionState.ACCEPTED
    assert updated.accepted_by_user_id == desk.id


async def test_business_owner_cannot_accept_via_whatsapp(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, venues=[venue], phone_number=OWNER_PHONE)

    with patch("app.core.twilio_client.send_whatsapp_text"):
        session = await _create_session(client, owner, venue)

    code = session_service.short_code(session["id"])
    resp, mock_send = await _post_webhook(client, OWNER_PHONE, f"ACCEPT-{code}")

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "Only valet desk staff" in mock_send.call_args[0][1]

    updated = await db.get(ValetSession, session["id"])
    assert updated.state == SessionState.REQUESTED


async def test_unknown_code_gets_friendly_reply(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue], phone_number=DESK_PHONE)

    resp, mock_send = await _post_webhook(client, DESK_PHONE, "ACCEPT-ZZZZZZ")

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "wasn't found" in mock_send.call_args[0][1]


async def test_whatsapp_accept_loses_race_to_app_accept(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, phone_number=OWNER_PHONE)
    desk1 = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue], phone_number=DESK_PHONE)
    desk2 = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue], phone_number="+919000000003")

    with patch("app.core.twilio_client.send_whatsapp_text"):
        session = await _create_session(client, owner, venue)

    # desk1 accepts through the app first.
    accept_resp = await client.post(f"/sessions/{session['id']}/accept", headers=auth_header(desk1))
    assert accept_resp.status_code == 200

    code = session_service.short_code(session["id"])
    resp, mock_send = await _post_webhook(client, "+919000000003", f"ACCEPT-{code}")

    assert resp.status_code == 200
    mock_send.assert_called_once()
    # By the time desk2's WhatsApp reply arrives, the session is no longer
    # REQUESTED/unaccepted at all, so it doesn't even show up as a candidate.
    assert "already been claimed" in mock_send.call_args[0][1]

    updated = await db.get(ValetSession, session["id"])
    assert updated.accepted_by_user_id == desk1.id
    assert updated.accepted_by_user_id != desk2.id


async def test_guest_message_from_unknown_number_still_routes_to_guest_flow(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    from app.models.parking import QRCode

    qr = QRCode(venue_id=venue.id, token="tok-1", label="Main")
    db.add(qr)
    await db.commit()

    resp, mock_send = await _post_webhook(client, "+911234567890", "QR:tok-1")

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "registration number" in mock_send.call_args[0][1]
