from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.prompts import CLASSIFIER_SYSTEM_PROMPT
from src.settings import get_settings


class MessageClassifier:
    def __init__(self):
        settings = get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.0,
        )

    def classify(self, message: str) -> Literal["general", "urgency", "emergency"]:
        """Clasifica un mensaje del paciente en una de las tres categorías."""
        messages = [
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]

        response = self.llm.invoke(messages)
        classification = response.content.strip().lower()

        valid_classifications = ["general", "urgency", "emergency"]
        if classification not in valid_classifications:
            return "general"

        return classification
