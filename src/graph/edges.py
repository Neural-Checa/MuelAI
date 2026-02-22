from typing import Literal

from src.graph.state import ConversationState


def route_after_patient_check(
    state: ConversationState,
) -> Literal["register_patient", "classify_message"]:
    """Decide si registrar paciente nuevo o clasificar mensaje."""
    if state["patient_exists"]:
        return "classify_message"
    return "register_patient"


def route_after_classification(
    state: ConversationState,
) -> Literal["handle_general_query", "handle_dental_urgency", "handle_medical_emergency"]:
    """Dirige al nodo correspondiente según la clasificación."""
    classification = state["classification"]

    if classification == "general":
        return "handle_general_query"
    elif classification == "urgency":
        return "handle_dental_urgency"
    else:
        return "handle_medical_emergency"


def route_after_urgency_check(
    state: ConversationState,
) -> Literal["connect_doctor", "wait_human_intervention"]:
    """Decide si conectar con doctor disponible o esperar intervención humana."""
    available_doctors = state.get("available_doctors", [])

    if available_doctors:
        return "connect_doctor"
    return "wait_human_intervention"


def should_continue_urgency_loop(
    state: ConversationState,
) -> Literal["check_availability", "end_conversation"]:
    """Determina si continuar el loop de urgencia o finalizar."""
    if state.get("assigned_doctor"):
        return "end_conversation"
    if state.get("human_response"):
        return "check_availability"
    return "end_conversation"
