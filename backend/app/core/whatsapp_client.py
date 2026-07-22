import hashlib
import hmac
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"


def send_whatsapp_text(to: str, body: str) -> None:
    """Sends a plain-text WhatsApp message via the Meta Cloud API. `to` is
    a plain phone number (e.g. "+919999999999"); Meta expects bare digits,
    no "+", so it's stripped here.

    Failures are logged, not raised -- a failed guest notification must
    never break the staff-facing action (e.g. marking a car parked) that
    triggered it.
    """
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code >= 400:
            logger.error("Failed to send WhatsApp message to %s: HTTP %s %s", to, resp.status_code, resp.text)
    except httpx.HTTPError as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", to, exc)


def verify_webhook_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verifies Meta's X-Hub-Signature-256 header: sha256=<HMAC-SHA256 hex
    digest of the raw request body, keyed with the App Secret>."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(settings.whatsapp_app_secret.encode(), payload, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
