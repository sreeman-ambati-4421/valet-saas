import logging

from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)


def _client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send_whatsapp_text(to: str, body: str) -> None:
    """Sends a plain-text WhatsApp message. `to` is a plain phone number
    (e.g. "+919999999999"), not prefixed with "whatsapp:".

    Failures are logged, not raised -- a failed guest notification must
    never break the staff-facing action (e.g. marking a car parked) that
    triggered it.
    """
    try:
        _client().messages.create(
            from_=settings.twilio_whatsapp_number,
            to=f"whatsapp:{to}",
            body=body,
        )
    except TwilioRestException as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", to, exc)


def verify_webhook_signature(url: str, params: dict, signature: str) -> bool:
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, params, signature)
