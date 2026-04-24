from src.graph.edges import (
    route_after_classification,
    route_after_patient_check,
    route_after_urgency,
    route_after_urgency_check,
)
from src.graph.graph import build_graph, get_initial_state


def test_initial_state_structure() -> None:
    state = get_initial_state("999888777")

    assert "messages" in state
    assert "patient_phone" in state
    assert "patient_id" in state
    assert "patient_exists" in state
    assert "classification" in state
    assert "awaiting_human" in state
    assert "available_doctors" in state

    assert state["patient_phone"] == "999888777"
    assert state["patient_exists"] is False
    assert state["messages"] == []


def test_route_after_patient_check_existing() -> None:
    state = {
        "patient_exists": True,
        "patient_id": 1,
    }
    assert route_after_patient_check(state) == "classify_message"


def test_route_after_patient_check_new() -> None:
    state = {
        "patient_exists": False,
        "patient_id": None,
    }
    assert route_after_patient_check(state) == "register_patient"


def test_route_after_classification_general() -> None:
    state = {"classification": "general"}
    assert route_after_classification(state) == "handle_general_query"


def test_route_after_classification_urgency() -> None:
    state = {"classification": "urgency"}
    assert route_after_classification(state) == "handle_dental_urgency"


def test_route_after_classification_emergency() -> None:
    state = {"classification": "emergency"}
    assert route_after_classification(state) == "handle_medical_emergency"


def test_awaiting_human_flow() -> None:
    state = {
        "patient_exists": True,
        "awaiting_human": True,
    }

    assert route_after_patient_check(state) == "check_availability"
    assert route_after_patient_check(state) != "classify_message"


def test_route_after_urgency_keys() -> None:
    state_with_doctors = {"available_doctors": [{"doctor_id": 1}]}
    state_without_doctors = {"available_doctors": []}

    assert route_after_urgency(state_with_doctors) == "connect_doctor"
    assert route_after_urgency(state_without_doctors) == "still_waiting"
    assert route_after_urgency(state_with_doctors) in {"connect_doctor", "still_waiting"}
    assert route_after_urgency(state_without_doctors) in {"connect_doctor", "still_waiting"}


def test_route_after_urgency_check_keys() -> None:
    state_with_doctors = {"available_doctors": [{"doctor_id": 1}]}
    state_without_doctors = {"available_doctors": []}

    assert route_after_urgency_check(state_with_doctors) == "connect_doctor"
    assert route_after_urgency_check(state_without_doctors) == "still_waiting"
    assert route_after_urgency_check(state_with_doctors) in {"connect_doctor", "still_waiting"}
    assert route_after_urgency_check(state_without_doctors) in {"connect_doctor", "still_waiting"}


def test_graph_compiles() -> None:
    graph = build_graph()
    nodes = set(graph.get_graph().nodes.keys())

    expected_nodes = {
        "verify_patient",
        "register_patient",
        "classify_message",
        "handle_general_query",
        "handle_dental_urgency",
        "check_availability",
        "connect_doctor",
        "handle_medical_emergency",
    }
    assert expected_nodes.issubset(nodes)
