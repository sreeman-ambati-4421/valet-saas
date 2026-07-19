from unittest.mock import patch

from sqlalchemy import select

from app.models.parking import QRCode
from app.models.session import SessionState, ValetSession
from app.models.user import UserRole
from app.models.vehicle_guest import Guest, Vehicle
from tests.conftest import auth_header, make_tenant, make_user, make_venue

GUEST_PHONE = "+911111111111"


async def _make_qr(db, venue, token="test-token"):
    qr = QRCode(venue_id=venue.id, token=token, label="Main Entrance")
    db.add(qr)
    await db.commit()
    await db.refresh(qr)
    return qr


async def _make_active_session(db, tenant, venue, guest_phone, state):
    guest = Guest(whatsapp_phone_number=guest_phone)
    db.add(guest)
    await db.flush()
    vehicle = Vehicle(registration_number="XY1234")
    db.add(vehicle)
    await db.flush()
    session = ValetSession(
        tenant_id=tenant.id,
        venue_id=venue.id,
        guest_id=guest.id,
        vehicle_id=vehicle.id,
        state=state,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


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


async def test_qr_scan_then_reg_number_creates_session(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    qr = await _make_qr(db, venue)

    resp1, mock_send1 = await _post_webhook(client, GUEST_PHONE, f"QR:{qr.token}")
    assert resp1.status_code == 200
    mock_send1.assert_called_once()
    assert "registration number" in mock_send1.call_args[0][1]

    resp2, mock_send2 = await _post_webhook(client, GUEST_PHONE, "ka01 ab 1234")
    assert resp2.status_code == 200
    mock_send2.assert_called_once()

    result = await db.execute(select(ValetSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].state == SessionState.REQUESTED
    assert sessions[0].venue_id == venue.id

    guest_result = await db.execute(select(Guest))
    guest = guest_result.scalars().first()
    assert guest.pending_venue_id is None


async def test_unknown_qr_token_no_session_created(client, db):
    resp, mock_send = await _post_webhook(client, GUEST_PHONE, "QR:does-not-exist")
    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "isn't valid" in mock_send.call_args[0][1]

    result = await db.execute(select(ValetSession))
    assert result.scalars().all() == []


async def test_keyword_car_while_parked_transitions_to_retrieval_requested(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    session = await _make_active_session(db, tenant, venue, GUEST_PHONE, state=SessionState.PARKED)

    resp, mock_send = await _post_webhook(client, GUEST_PHONE, "car")
    assert resp.status_code == 200
    mock_send.assert_called_once()

    await db.refresh(session)
    assert session.state == SessionState.RETRIEVAL_REQUESTED


async def test_keyword_car_while_requested_state_no_transition(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    session = await _make_active_session(db, tenant, venue, GUEST_PHONE, state=SessionState.REQUESTED)

    resp, mock_send = await _post_webhook(client, GUEST_PHONE, "car")
    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "status" in mock_send.call_args[0][1].lower()

    await db.refresh(session)
    assert session.state == SessionState.REQUESTED


async def test_invalid_signature_returns_403(client, db):
    with patch("app.core.twilio_client.verify_webhook_signature", return_value=False), patch(
        "app.core.twilio_client.send_whatsapp_text"
    ) as mock_send:
        resp = await client.post(
            "/webhooks/twilio/whatsapp",
            data={"From": f"whatsapp:{GUEST_PHONE}", "Body": "QR:whatever"},
            headers={"X-Twilio-Signature": "bad"},
        )
    assert resp.status_code == 403
    mock_send.assert_not_called()


async def test_staff_parking_session_sends_guest_whatsapp(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    manager = await make_user(db, UserRole.VENUE_MANAGER, tenant=tenant, venues=[venue])
    valet = await make_user(db, UserRole.VALET, tenant=tenant, venues=[venue])

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": "XY1234", "guest_phone_number": GUEST_PHONE},
        headers=auth_header(manager),
    )
    sid = create_resp.json()["id"]
    await client.post(f"/sessions/{sid}/accept", headers=auth_header(valet))
    await client.post(f"/sessions/{sid}/collected", headers=auth_header(valet))

    with patch("app.core.twilio_client.send_whatsapp_text") as mock_send:
        park_resp = await client.post(
            f"/sessions/{sid}/park",
            json={"key_tag": "K-1", "parking_zone_id": None, "parking_slot_id": None},
            headers=auth_header(valet),
        )

    assert park_resp.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == GUEST_PHONE
