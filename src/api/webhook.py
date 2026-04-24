import logging
from typing import Annotated

from fastapi import APIRouter, Form, Response, status
from langchain_core.messages import AIMessage, HumanMessage

from src.api.twilio_client import TwilioClient
from src.graph.graph import build_graph

logger = logging.getLogger(__name__)
router = APIRouter()
_graph = build_graph()
_twilio_client = TwilioClient()


def normalize_phone(raw: str) -> str:
    if raw.startswith("whatsapp:"):
        return raw.split("whatsapp:", 1)[1].strip()
    return raw.strip()


def _extract_last_ai_message(result_state: dict) -> str:
    messages = result_state.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return str(message.content)
    return "Gracias por contactarnos. Hemos recibido tu mensaje y te responderemos pronto."


@router.post("/twilio", status_code=status.HTTP_200_OK)
def twilio_webhook(
    from_number: Annotated[str, Form(alias="From")],
    body: Annotated[str, Form(alias="Body")],
) -> Response:
    phone = normalize_phone(from_number)

    state = {
        "messages": [HumanMessage(content=body)],
        "patient_phone": phone,
    }
    config = {"configurable": {"thread_id": phone}}

    try:
        result = _graph.invoke(state, config)
        ai_response = _extract_last_ai_message(result)
        _twilio_client.send_whatsapp_message(to=phone, body=ai_response)
    except Exception:
        logger.exception("Error while processing Twilio webhook for %s", phone)

    return Response(content="", status_code=status.HTTP_200_OK)
