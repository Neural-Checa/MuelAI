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
) -> Literal["select_slot", "wait_human_intervention", "end_conversation"]:
    """Decide si mostrar slots, esperar intervención humana o finalizar."""
    available_doctors = state.get("available_doctors", [])

    if available_doctors:
        return "select_slot"
    # Si venimos de check_availability y no hay doctores, finalizar
    if state.get("from_check_availability"):
        return "end_conversation"
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
