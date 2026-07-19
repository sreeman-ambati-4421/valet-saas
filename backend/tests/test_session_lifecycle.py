import asyncio

from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


async def _setup(db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    manager = await make_user(db, UserRole.VENUE_MANAGER, tenant=tenant, venues=[venue])
    valet = await make_user(db, UserRole.VALET, tenant=tenant, venues=[venue])
    other_valet = await make_user(db, UserRole.VALET, tenant=tenant, venues=[venue])
    return tenant, venue, manager, valet, other_valet


async def test_full_session_walkthrough_and_audit_trail(client, db):
    tenant, venue, manager, valet, _ = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": " ka01 ab 1234 ", "guest_phone_number": "+919999999999", "guest_name": "Sree"},
        headers=auth_header(manager),
    )
    assert create_resp.status_code == 201
    session = create_resp.json()
    assert session["state"] == "REQUESTED"
    assert session["registration_number"] == "KA01AB1234"  # normalized
    sid = session["id"]

    accept_resp = await client.post(f"/sessions/{sid}/accept", headers=auth_header(valet))
    assert accept_resp.status_code == 200
    assert accept_resp.json()["state"] == "ASSIGNED"
    assert accept_resp.json()["assigned_valet_id"] == valet.id

    steps = [
        ("collected", None, "VEHICLE_COLLECTED"),
        ("park", {"key_tag": "K-42", "parking_zone_id": None, "parking_slot_id": None}, "PARKED"),
        ("request-retrieval", None, "RETRIEVAL_REQUESTED"),
        ("retrieve", None, "RETRIEVING"),
        ("ready", None, "READY"),
        ("deliver", None, "DELIVERED"),
    ]
    for path, body, expected_state in steps:
        if body is not None:
            resp = await client.post(f"/sessions/{sid}/{path}", json=body, headers=auth_header(valet))
        else:
            resp = await client.post(f"/sessions/{sid}/{path}", headers=auth_header(valet))
        assert resp.status_code == 200, f"{path} failed: {resp.text}"
        assert resp.json()["state"] == expected_state

    detail_resp = await client.get(f"/sessions/{sid}", headers=auth_header(manager))
    assert detail_resp.status_code == 200
    events = detail_resp.json()["events"]
    # created + 7 transitions = 8 events
    assert len(events) == 8
    assert [e["to_state"] for e in events] == [
        "REQUESTED",
        "ASSIGNED",
        "VEHICLE_COLLECTED",
        "PARKED",
        "RETRIEVAL_REQUESTED",
        "RETRIEVING",
        "READY",
        "DELIVERED",
    ]


async def test_out_of_order_transition_is_rejected(client, db):
    tenant, venue, manager, valet, _ = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": "XY1234", "guest_phone_number": "+911111111111"},
        headers=auth_header(manager),
    )
    sid = create_resp.json()["id"]

    # Still REQUESTED -- cannot jump straight to deliver.
    resp = await client.post(f"/sessions/{sid}/deliver", headers=auth_header(valet))

    assert resp.status_code == 403  # not the assigned valet yet (nobody is)


async def test_unassigned_valet_cannot_progress_someone_elses_job(client, db):
    tenant, venue, manager, valet, other_valet = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": "XY1234", "guest_phone_number": "+911111111111"},
        headers=auth_header(manager),
    )
    sid = create_resp.json()["id"]
    await client.post(f"/sessions/{sid}/accept", headers=auth_header(valet))

    resp = await client.post(f"/sessions/{sid}/collected", headers=auth_header(other_valet))

    assert resp.status_code == 403


async def test_concurrent_accept_only_one_valet_wins(client, db):
    tenant, venue, manager, valet, other_valet = await _setup(db)

    create_resp = await client.post(
        f"/venues/{venue.id}/sessions",
        json={"registration_number": "XY1234", "guest_phone_number": "+911111111111"},
        headers=auth_header(manager),
    )
    sid = create_resp.json()["id"]

    results = await asyncio.gather(
        client.post(f"/sessions/{sid}/accept", headers=auth_header(valet)),
        client.post(f"/sessions/{sid}/accept", headers=auth_header(other_valet)),
    )

    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 409]
