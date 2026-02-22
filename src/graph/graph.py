from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.graph.edges import (
    route_after_classification,
    route_after_patient_check,
    route_after_urgency_check,
)
from src.graph.nodes import (
    check_doctor_availability,
    classify_message,
    handle_dental_urgency,
    handle_general_query,
    handle_medical_emergency,
    register_patient,
    select_appointment_slot,
    verify_patient,
)
from src.graph.state import ConversationState


def create_dental_graph():
    """Crea y retorna el grafo de LangGraph para el asistente dental."""

    graph = StateGraph(ConversationState)

    graph.add_node("verify_patient", verify_patient)
    graph.add_node("register_patient", register_patient)
    graph.add_node("classify_message", classify_message)
    graph.add_node("handle_general_query", handle_general_query)
    graph.add_node("handle_dental_urgency", handle_dental_urgency)
    graph.add_node("handle_medical_emergency", handle_medical_emergency)
    graph.add_node("check_availability", check_doctor_availability)
    graph.add_node("select_slot", select_appointment_slot)

    graph.set_entry_point("verify_patient")

    graph.add_conditional_edges(
        "verify_patient",
        route_after_patient_check,
        {
            "register_patient": "register_patient",
            "classify_message": "classify_message",
        },
    )

    graph.add_edge("register_patient", "classify_message")

    graph.add_conditional_edges(
        "classify_message",
        route_after_classification,
        {
            "handle_general_query": "handle_general_query",
            "handle_dental_urgency": "handle_dental_urgency",
            "handle_medical_emergency": "handle_medical_emergency",
        },
    )

    graph.add_edge("handle_general_query", END)

    graph.add_conditional_edges(
        "handle_dental_urgency",
        route_after_urgency_check,
        {
            "select_slot": "select_slot",
            "wait_human_intervention": "check_availability",
            "end_conversation": END,
        },
    )

    graph.add_conditional_edges(
        "check_availability",
        route_after_urgency_check,
        {
            "select_slot": "select_slot",
            "wait_human_intervention": "check_availability",
            "end_conversation": END,
        },
    )

    graph.add_edge("select_slot", END)

    graph.add_edge("handle_medical_emergency", END)

    memory = MemorySaver()
    compiled_graph = graph.compile(checkpointer=memory)

    return compiled_graph


def get_initial_state(patient_phone: str | None = None) -> ConversationState:
    """Retorna el estado inicial para una nueva conversación."""
    return {
        "messages": [],
        "patient_phone": patient_phone,
        "patient_id": None,
        "patient_exists": False,
        "patient_name": None,
        "classification": None,
        "medical_history": None,
        "awaiting_human": False,
        "awaiting_slot_selection": False,
        "available_doctors": [],
        "available_slots": [],
        "selected_slot": None,
        "assigned_doctor": None,
        "appointment_confirmed": None,
        "emergency_contacts_provided": False,
        "from_check_availability": False,
        "human_response": None,
    }
