from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from src.schemas.models import DoctorAvailability


class ConversationState(TypedDict):
    """Estado de la conversación en el grafo de LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]

    patient_dni: Optional[str]

    patient_id: Optional[int]

    patient_exists: bool

    patient_name: Optional[str]

    classification: Optional[Literal["general", "urgency", "emergency"]]

    medical_history: Optional[str]

    awaiting_human: bool

    available_doctors: list[dict]

    assigned_doctor: Optional[dict]

    emergency_contacts_provided: bool

    human_response: Optional[str]

    appointment_info: Optional[str]

    # Slots disponibles para que el paciente seleccione
    available_slots: Optional[list[dict]]

    # Indica que el doctor se unió al chat (HITL nivel 2)
    doctor_in_chat: bool
