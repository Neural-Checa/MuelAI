from typing import Literal

from src.graph.state import ConversationState


def route_after_patient_check(
    state: ConversationState,
) -> Literal["register_patient", "classify_message", "check_availability"]:
    """Decide si registrar paciente nuevo o clasificar mensaje."""
    if not state["patient_exists"]:
        return "register_patient"

    if state.get("awaiting_human"):
        return "check_availability"

    return "classify_message"


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


def route_after_patient_flow(
    state: ConversationState,
) -> Literal["check_availability", "classify_message"]:
    """En contexto stateless, prioriza re-chequear disponibilidad si estaba en espera."""
    if state.get("awaiting_human"):
        return "check_availability"
    return "classify_message"


def route_after_urgency(
    state: ConversationState,
) -> Literal["connect_doctor", "still_waiting"]:
    """Ruta posterior al manejo de urgencia inicial."""
    available_doctors = state.get("available_doctors", [])

    if available_doctors:
        return "connect_doctor"
    return "still_waiting"


def route_after_urgency_check(
    state: ConversationState,
) -> Literal["connect_doctor", "still_waiting"]:
    """Ruta después del re-chequeo de disponibilidad."""
    available_doctors = state.get("available_doctors", [])

    if available_doctors:
        return "connect_doctor"
    return "still_waiting"
