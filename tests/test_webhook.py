import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

# Ensure required settings exist before importing the app/router modules.
os.environ.setdefault("GOOGLE_API_KEY", "dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "dummy")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")

import main
from src.api.webhook import normalize_phone


client = TestClient(main.app)


def test_health_check() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "MuelAI"}


def test_normalize_phone() -> None:
    assert normalize_phone("whatsapp:+51987654321") == "+51987654321"
    assert normalize_phone("+51987654321") == "+51987654321"
    assert normalize_phone("whatsapp:+14155238886") == "+14155238886"


def test_webhook_missing_body() -> None:
    response = client.post("/webhook/twilio", data={})
    assert response.status_code == 422


def test_webhook_uses_graph_and_twilio_mocks() -> None:
    with patch("src.api.webhook._graph") as graph_mock, patch(
        "src.api.webhook._twilio_client"
    ) as twilio_mock:
        graph_mock.invoke.return_value = {
            "messages": [AIMessage(content="Respuesta simulada")]
        }

        response = client.post(
            "/webhook/twilio",
            data={"From": "whatsapp:+51987654321", "Body": "Hola"},
        )

        assert response.status_code == 200
        graph_mock.invoke.assert_called_once()
        twilio_mock.send_whatsapp_message.assert_called_once_with(
            to="+51987654321",
            body="Respuesta simulada",
        )
