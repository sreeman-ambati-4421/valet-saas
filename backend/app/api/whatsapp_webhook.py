import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import whatsapp_client
from app.core.config import settings
from app.core.db import get_db
from app.services import guest_conversation_service, staff_conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["whatsapp-webhook"])


@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(request: Request) -> Response:
    """Meta calls this once, when the webhook URL is configured in the App
    dashboard (and again if you ever re-verify it). Must echo back
    hub.challenge with a 200 if the mode and verify token match what's
    configured; otherwise reject."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and settings.whatsapp_verify_token and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verification succeeded")
        return Response(content=challenge, media_type="text/plain", status_code=status.HTTP_200_OK)

    logger.warning("WhatsApp webhook verification failed (mode=%s)", mode)
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not whatsapp_client.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        logger.warning("WhatsApp webhook received a body that could not be parsed as JSON")
        return Response(status_code=status.HTTP_200_OK)

    if not isinstance(payload, dict):
        logger.warning("WhatsApp webhook payload was not a JSON object")
        return Response(status_code=status.HTTP_200_OK)

    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}

            statuses = value.get("statuses") or []
            if statuses:
                # Delivery/read receipts -- nothing to do with these yet.
                logger.debug("Ignoring %d WhatsApp status update(s)", len(statuses))

            for message in value.get("messages") or []:
                if isinstance(message, dict):
                    await _handle_message(db, message)

    # Always 200, quickly -- Meta retries (and can eventually disable the
    # webhook) if it doesn't get a fast 2xx.
    return Response(status_code=status.HTTP_200_OK)


async def _handle_message(db: AsyncSession, message: dict) -> None:
    from_number = message.get("from")
    if not from_number:
        return

    # Meta sends bare digits ("919876543210"); our phone numbers are
    # stored E.164 with a leading "+".
    from_phone = from_number if str(from_number).startswith("+") else f"+{from_number}"

    message_type = message.get("type")
    body = (message.get("text") or {}).get("body", "") if message_type == "text" else ""

    logger.info(
        "Received WhatsApp message: from=%s message_id=%s type=%s",
        from_phone,
        message.get("id"),
        message_type,
    )

    staff_user = await staff_conversation_service.find_staff_user(db, from_phone)
    if staff_user is not None:
        await staff_conversation_service.handle_inbound_message(db, staff_user, body)
    else:
        await guest_conversation_service.handle_inbound_message(db, from_phone, body)
