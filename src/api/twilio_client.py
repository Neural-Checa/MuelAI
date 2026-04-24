import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from src.settings import get_settings

logger = logging.getLogger(__name__)


class TwilioClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._from_number = settings.twilio_phone_number
        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    def send_whatsapp_message(self, to: str, body: str) -> None:
        """Send a WhatsApp message and swallow Twilio errors to keep webhook stable."""
        try:
            self._client.messages.create(
                from_=self._from_number,
                to=f"whatsapp:{to}",
                body=body,
            )
        except TwilioRestException:
            logger.exception("Twilio REST error while sending WhatsApp message to %s", to)
        except Exception:
            logger.exception("Unexpected error while sending WhatsApp message to %s", to)
