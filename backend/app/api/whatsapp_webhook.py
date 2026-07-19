from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import twilio_client
from app.core.config import settings
from app.core.db import get_db
from app.services import guest_conversation_service

router = APIRouter(tags=["whatsapp-webhook"])


@router.post("/webhooks/twilio/whatsapp")
async def twilio_whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    form = await request.form()
    params = dict(form)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.public_base_url}{request.url.path}"

    if not twilio_client.verify_webhook_signature(url, params, signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid Twilio signature")

    from_phone = str(params.get("From", "")).replace("whatsapp:", "")
    body = str(params.get("Body", ""))

    if from_phone:
        await guest_conversation_service.handle_inbound_message(db, from_phone, body)

    # Empty 200 (not TwiML) -- replies are sent via the REST API from
    # guest_conversation_service, not as an auto-reply in this response.
    return Response(status_code=200)
