import hashlib
import hmac
import json
from unittest.mock import patch

from app.core.config import settings

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


def _sign(body: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _message_payload(from_phone: str = "911111111111", message_type: str = "text", body: str = "hi") -> dict:
    message: dict = {"from": from_phone, "id": "wamid.test", "type": message_type, "timestamp": "1700000000"}
    if message_type == "text":
        message["text"] = {"body": body}
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


async def test_get_verification_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", VERIFY_TOKEN)

    resp = await client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )

    assert resp.status_code == 200
    assert resp.text == "12345"


async def test_get_verification_fails_with_wrong_token(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", VERIFY_TOKEN)

    resp = await client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )

    assert resp.status_code == 403


async def test_get_verification_fails_with_wrong_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", VERIFY_TOKEN)

    resp = await client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "unsubscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )

    assert resp.status_code == 403


async def test_post_missing_signature_header_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)

    resp = await client.post("/webhooks/whatsapp", json=_message_payload())

    assert resp.status_code == 403


async def test_post_invalid_signature_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)

    resp = await client.post(
        "/webhooks/whatsapp",
        json=_message_payload(),
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )

    assert resp.status_code == 403


async def test_post_valid_signature_with_real_hmac_is_accepted(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)
    body = b'{"entry": []}'

    with patch("app.core.whatsapp_client.send_whatsapp_text"):
        resp = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
        )

    assert resp.status_code == 200


async def test_post_non_json_body_returns_200(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)
    body = b"not json"

    resp = await client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
    )

    assert resp.status_code == 200


async def test_post_status_only_event_is_ignored(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.x", "status": "delivered"}]}}]}]}
    body = json.dumps(payload).encode()

    with patch("app.core.whatsapp_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    mock_send.assert_not_called()


async def test_post_non_text_message_type_does_not_crash(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", APP_SECRET)
    payload = _message_payload(message_type="image")
    body = json.dumps(payload).encode()

    with patch("app.core.whatsapp_client.send_whatsapp_text") as mock_send:
        resp = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"X-Hub-Signature-256": _sign(body), "Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    # Unknown number, empty body -> guest flow's "no active session" reply.
    mock_send.assert_called_once()
