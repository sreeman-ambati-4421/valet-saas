import asyncio

from app.models.user import UserRole
from tests.conftest import auth_header, make_qr_code, make_tenant, make_user, make_venue


async def _setup(db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant, venues=[venue])
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])
    other_desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])
    await make_qr_code(db, venue)
    return tenant, venue, owner, desk, other_desk


async def test_full_session_walkthrough_and_audit_trail(client, db):
    tenant, venue, owner, desk, _ = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": "+919999999999", "guest_name": "Sree"},
        headers=auth_header(owner),
    )
    assert create_resp.status_code == 201
    session = create_resp.json()
    assert session["state"] == "REQUESTED"
    assert session["registration_number"] is None
    assert session["tag_label"] == "Tag 1"
    sid = session["id"]

    accept_resp = await client.post(f"/sessions/{sid}/accept", headers=auth_header(desk))
    assert accept_resp.status_code == 200
    assert accept_resp.json()["state"] == "ACCEPTED"
    assert accept_resp.json()["accepted_by_user_id"] == desk.id

    steps = [
        ("park", {"registration_number": " ka01 ab 1234 "}, "PARKED"),
        ("request-retrieval", None, "RETRIEVAL_REQUESTED"),
        ("retrieving", None, "RETRIEVING"),
        ("ready", None, "READY"),
        ("complete", None, "COMPLETED"),
    ]
    for path, body, expected_state in steps:
        if body is not None:
            resp = await client.post(f"/sessions/{sid}/{path}", json=body, headers=auth_header(desk))
        else:
            resp = await client.post(f"/sessions/{sid}/{path}", headers=auth_header(desk))
        assert resp.status_code == 200, f"{path} failed: {resp.text}"
        assert resp.json()["state"] == expected_state

    assert resp.json()["registration_number"] == "KA01AB1234"  # normalized, set at park

    detail_resp = await client.get(f"/sessions/{sid}", headers=auth_header(owner))
    assert detail_resp.status_code == 200
    events = detail_resp.json()["events"]
    # created + 6 transitions = 7 events
    assert len(events) == 7
    assert [e["to_state"] for e in events] == [
        "REQUESTED",
        "ACCEPTED",
        "PARKED",
        "RETRIEVAL_REQUESTED",
        "RETRIEVING",
        "READY",
        "COMPLETED",
    ]

    # The tag is released back to the pool once the session completes.
    tags_resp = await client.get(f"/venues/{venue.id}/qr-codes", headers=auth_header(owner))
    assert tags_resp.json()[0]["status"] == "available"


async def test_out_of_order_transition_is_rejected(client, db):
    tenant, venue, owner, desk, _ = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": "+911111111111"},
        headers=auth_header(owner),
    )
    sid = create_resp.json()["id"]

    # Still REQUESTED -- cannot jump straight to ready.
    resp = await client.post(f"/sessions/{sid}/ready", headers=auth_header(desk))

    assert resp.status_code == 403  # not the desk person who accepted it yet (nobody has)


async def test_unaccepted_desk_person_cannot_progress_someone_elses_job(client, db):
    tenant, venue, owner, desk, other_desk = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": "+911111111111"},
        headers=auth_header(owner),
    )
    sid = create_resp.json()["id"]
    await client.post(f"/sessions/{sid}/accept", headers=auth_header(desk))

    resp = await client.post(
        f"/sessions/{sid}/park",
        json={"registration_number": "XY1234"},
        headers=auth_header(other_desk),
    )

    assert resp.status_code == 403


async def test_concurrent_accept_only_one_desk_person_wins(client, db):
    tenant, venue, owner, desk, other_desk = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": "+911111111111"},
        headers=auth_header(owner),
    )
    sid = create_resp.json()["id"]

    results = await asyncio.gather(
        client.post(f"/sessions/{sid}/accept", headers=auth_header(desk)),
        client.post(f"/sessions/{sid}/accept", headers=auth_header(other_desk)),
    )

    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 409]
