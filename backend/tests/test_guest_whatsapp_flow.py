from unittest.mock import patch

from sqlalchemy import select

from app.models.parking import QRCode, TagStatus
from app.models.session import SessionState, ValetSession
from app.models.user import UserRole
from app.models.vehicle_guest import Guest, Vehicle
from tests.conftest import auth_header, make_qr_code, make_tenant, make_user, make_venue

GUEST_PHONE = "+911111111111"


async def _make_active_session(db, tenant, venue, guest_phone, state, created_via_whatsapp=False, qr_code_id=None):
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
        qr_code_id=qr_code_id,
        state=state,
        created_via_whatsapp=created_via_whatsapp,
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


async def test_qr_scan_creates_session_immediately(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    qr = await make_qr_code(db, venue, label="Tag 1")

    resp, mock_send = await _post_webhook(
        client, GUEST_PHONE, f"👋 Hi {venue.name}! My car needs to be parked -- tag {qr.token}."
    )
    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "We've got your request" in mock_send.call_args[0][1]

    result = await db.execute(select(ValetSession))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].state == SessionState.REQUESTED
    assert sessions[0].venue_id == venue.id
    assert sessions[0].created_via_whatsapp is True
    assert sessions[0].qr_code_id == qr.id
    assert sessions[0].vehicle_id is None  # not known until parked

    await db.refresh(qr)
    assert qr.status == TagStatus.IN_USE


async def test_scan_of_in_use_tag_is_rejected(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    qr = await make_qr_code(db, venue, status=TagStatus.IN_USE)

    resp, mock_send = await _post_webhook(
        client, GUEST_PHONE, f"👋 Hi {venue.name}! My car needs to be parked -- tag {qr.token}."
    )

    assert resp.status_code == 200
    mock_send.assert_called_once()
    assert "in use" in mock_send.call_args[0][1].lower()

    result = await db.execute(select(ValetSession))
    assert result.scalars().all() == []


async def test_unknown_qr_token_no_session_created(client, db):
    resp, mock_send = await _post_webhook(
        client, GUEST_PHONE, "👋 Hi Some Venue! My car needs to be parked -- tag ABCDEF."
    )
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
            data={"From": f"whatsapp:{GUEST_PHONE}", "Body": "👋 Hi Venue! My car needs to be parked -- tag ABCDEF."},
            headers={"X-Twilio-Signature": "bad"},
        )
    assert resp.status_code == 403
    mock_send.assert_not_called()


async def test_staff_cannot_manually_request_retrieval_on_whatsapp_originated_session(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, venues=[venue])
    session = await _make_active_session(
        db, tenant, venue, GUEST_PHONE, state=SessionState.PARKED, created_via_whatsapp=True
    )

    resp = await client.post(f"/sessions/{session.id}/request-retrieval", headers=auth_header(owner))

    assert resp.status_code == 403
    await db.refresh(session)
    assert session.state == SessionState.PARKED


async def test_staff_can_manually_request_retrieval_on_staff_created_session(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, venues=[venue])
    session = await _make_active_session(
        db, tenant, venue, GUEST_PHONE, state=SessionState.PARKED, created_via_whatsapp=False
    )

    resp = await client.post(f"/sessions/{session.id}/request-retrieval", headers=auth_header(owner))

    assert resp.status_code == 200
    assert resp.json()["state"] == "RETRIEVAL_REQUESTED"


async def test_staff_parking_session_sends_guest_whatsapp(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, venues=[venue])
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])
    await make_qr_code(db, venue)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": GUEST_PHONE},
        headers=auth_header(owner),
    )
    sid = create_resp.json()["id"]
    await client.post(f"/sessions/{sid}/accept", headers=auth_header(desk))

    with patch("app.core.twilio_client.send_whatsapp_text") as mock_send:
        park_resp = await client.post(
            f"/sessions/{sid}/park",
            json={"registration_number": "XY1234"},
            headers=auth_header(desk),
        )

    assert park_resp.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == GUEST_PHONE
