from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


async def test_business_owner_bulk_creates_tags(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    resp = await client.post(
        f"/venues/{venue.id}/qr-codes",
        json={"count": 3},
        headers=auth_header(owner),
    )

    assert resp.status_code == 201, resp.text
    tags = resp.json()
    assert len(tags) == 3
    labels = [t["label"] for t in tags]
    assert labels == ["Tag 1", "Tag 2", "Tag 3"]
    for tag in tags:
        assert tag["venue_id"] == venue.id
        assert tag["is_active"] is True
        assert tag["status"] == "available"
        assert tag["wa_link"].startswith("https://wa.me/")
        assert tag["token"] in tag["wa_link"]


async def test_repeated_generation_continues_numbering(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 2}, headers=auth_header(owner))
    resp = await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 2}, headers=auth_header(owner))

    labels = [t["label"] for t in resp.json()]
    assert labels == ["Tag 3", "Tag 4"]


async def test_list_qr_codes_for_venue(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 2}, headers=auth_header(owner))

    resp = await client.get(f"/venues/{venue.id}/qr-codes", headers=auth_header(owner))

    assert resp.status_code == 200
    labels = {qr["label"] for qr in resp.json()}
    assert labels == {"Tag 1", "Tag 2"}


async def test_list_qr_codes_filters_by_status(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)
    await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 2}, headers=auth_header(owner))

    # Claim one via a session so it's no longer available.
    await client.post(
        f"/venues/{venue.id}/sessions",
        json={"guest_phone_number": "+911111111111"},
        headers=auth_header(owner),
    )

    resp = await client.get(f"/venues/{venue.id}/qr-codes?status_filter=available", headers=auth_header(owner))
    assert len(resp.json()) == 1

    resp = await client.get(f"/venues/{venue.id}/qr-codes?status_filter=in_use", headers=auth_header(owner))
    assert len(resp.json()) == 1


async def test_qr_code_image_endpoint_returns_png(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    create_resp = await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 1}, headers=auth_header(owner))
    qr_id = create_resp.json()[0]["id"]

    # Deliberately unauthenticated -- guests scanning a printed code have no account.
    resp = await client.get(f"/qr-codes/{qr_id}/image")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


async def test_valet_desk_cannot_create_qr_codes(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])

    resp = await client.post(f"/venues/{venue.id}/qr-codes", json={"count": 1}, headers=auth_header(desk))

    assert resp.status_code == 403
