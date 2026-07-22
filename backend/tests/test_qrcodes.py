from app.models.user import UserRole
from tests.conftest import auth_header, make_tenant, make_user, make_venue


async def test_business_owner_creates_qr_code(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    resp = await client.post(
        f"/venues/{venue.id}/qr-codes",
        json={"label": "Main Entrance"},
        headers=auth_header(owner),
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["venue_id"] == venue.id
    assert body["label"] == "Main Entrance"
    assert body["is_active"] is True
    assert body["wa_link"].startswith("https://wa.me/")
    assert f"QR:{body['token']}" in body["wa_link"] or body["token"] in body["wa_link"]


async def test_list_qr_codes_for_venue(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    await client.post(f"/venues/{venue.id}/qr-codes", json={"label": "Gate 1"}, headers=auth_header(owner))
    await client.post(f"/venues/{venue.id}/qr-codes", json={"label": "Gate 2"}, headers=auth_header(owner))

    resp = await client.get(f"/venues/{venue.id}/qr-codes", headers=auth_header(owner))

    assert resp.status_code == 200
    labels = {qr["label"] for qr in resp.json()}
    assert labels == {"Gate 1", "Gate 2"}


async def test_qr_code_image_endpoint_returns_png(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    owner = await make_user(db, UserRole.BUSINESS_OWNER, tenant=tenant)

    create_resp = await client.post(
        f"/venues/{venue.id}/qr-codes", json={"label": "Main"}, headers=auth_header(owner)
    )
    qr_id = create_resp.json()["id"]

    # Deliberately unauthenticated -- guests scanning a printed code have no account.
    resp = await client.get(f"/qr-codes/{qr_id}/image")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


async def test_valet_desk_cannot_create_qr_code(client, db):
    tenant = await make_tenant(db)
    venue = await make_venue(db, tenant)
    desk = await make_user(db, UserRole.VALET_DESK, tenant=tenant, venues=[venue])

    resp = await client.post(f"/venues/{venue.id}/qr-codes", json={"label": "Main"}, headers=auth_header(desk))

    assert resp.status_code == 403
