from typing import Annotated, Any, Literal, Optional

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class ConversationState(TypedDict, total=False):
    """Estado de la conversación en el grafo de LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]

    patient_phone: Optional[str]
    patient_id: Optional[int]
    patient_exists: bool
    patient_name: Optional[str]

    classification: Optional[Literal["general", "urgency", "emergency"]]

    medical_history: Optional[str]

    awaiting_human: bool
    awaiting_slot_selection: bool

    available_doctors: list[dict]
    available_slots: list[dict]
    selected_slot: Optional[dict]

    assigned_doctor: Optional[dict]
    appointment_confirmed: Optional[dict]

    emergency_contacts_provided: bool

    from_check_availability: bool

    human_response: Optional[Any]
