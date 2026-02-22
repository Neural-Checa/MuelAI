from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.prompts import (
    DENTAL_ASSISTANT_SYSTEM_PROMPT,
    EMERGENCY_HANDLER_PROMPT,
    URGENCY_HANDLER_PROMPT,
)
from src.settings import get_settings


class DentalResponder:
    def __init__(self):
        settings = get_settings()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.7,
        )

    def respond_general_query(
        self,
        user_message: str,
        medical_history: str,
        patient_name: str,
        conversation_history: list[BaseMessage] | None = None,
    ) -> str:
        """Genera una respuesta para consultas generales."""
        context = f"""
Información del paciente:
- Nombre: {patient_name}

{medical_history}
"""
        messages = [
            SystemMessage(content=DENTAL_ASSISTANT_SYSTEM_PROMPT),
            SystemMessage(content=f"Contexto del paciente:\n{context}"),
        ]

        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        messages.append(HumanMessage(content=user_message))

        response = self.llm.invoke(messages)
        return response.content

    def respond_urgency(
        self,
        user_message: str,
        available_doctors: list[dict],
        patient_name: str,
    ) -> str:
        """Genera una respuesta para urgencias dentales."""
        if available_doctors:
            doctors_info = "\n".join(
                [
                    f"- {doc['doctor_name']} ({doc['specialty']})"
                    for doc in available_doctors
                ]
            )
            context = f"""
Paciente: {patient_name}
Doctores disponibles:
{doctors_info}
"""
        else:
            context = f"""
Paciente: {patient_name}
Estado: No hay doctores disponibles en este momento.
Un operador humano ha sido notificado para asistir.
"""

        messages = [
            SystemMessage(content=URGENCY_HANDLER_PROMPT),
            SystemMessage(content=context),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        return response.content

    def respond_emergency(self, user_message: str, patient_name: str) -> str:
        """Genera una respuesta para emergencias médicas."""
        emergency_contacts = """
CONTACTOS DE EMERGENCIA:
- Emergencias (SAMU): 106
- Bomberos: 116
- Policía Nacional: 105
- Cruz Roja: (01) 266-0481

Por favor, llame a estos números INMEDIATAMENTE si su vida está en peligro.
"""

        messages = [
            SystemMessage(content=EMERGENCY_HANDLER_PROMPT),
            SystemMessage(content=f"Paciente: {patient_name}\n\n{emergency_contacts}"),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        return response.content
