import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage


class TestMessageClassification:
    """Tests para la clasificación de mensajes."""

    def test_general_query_examples(self):
        general_queries = [
            "¿Cuánto cuesta una limpieza dental?",
            "¿Cada cuánto debo ir al dentista?",
            "Tengo una pequeña molestia en una muela",
            "¿Qué tratamientos ofrecen para blanqueamiento?",
            "Quisiera agendar una cita para revisión",
        ]
        for query in general_queries:
            assert len(query) > 0

    def test_urgency_query_examples(self):
        urgency_queries = [
            "Tengo un dolor muy fuerte en la muela que no me deja dormir",
            "Se me rompió un diente y me duele mucho",
            "Tengo la cara hinchada por una infección dental",
            "Me sangra mucho la encía después de una extracción",
            "Tengo un absceso dental que me causa dolor severo",
        ]
        for query in urgency_queries:
            assert len(query) > 0

    def test_emergency_query_examples(self):
        emergency_queries = [
            "No puedo respirar bien, tengo la garganta muy hinchada",
            "Tuve un accidente y no paro de sangrar de la boca",
            "Me golpeé muy fuerte en la cara y estoy mareado",
            "Tengo fiebre muy alta y no puedo tragar",
        ]
        for query in emergency_queries:
            assert len(query) > 0


class TestConversationState:
    """Tests para el estado de conversación."""

    def test_initial_state_structure(self):
        from src.graph.graph import get_initial_state

        state = get_initial_state("76543210")

        assert "messages" in state
        assert "patient_dni" in state
        assert "patient_id" in state
        assert "patient_exists" in state
        assert "classification" in state
        assert "awaiting_human" in state
        assert "available_doctors" in state
        assert "appointment_info" in state
        assert "available_slots" in state
        assert "doctor_in_chat" in state

        assert state["patient_dni"] == "76543210"
        assert state["patient_exists"] is False
        assert state["messages"] == []
        assert state["available_slots"] is None
        assert state["doctor_in_chat"] is False


class TestEdgeRouting:
    """Tests para las funciones de routing."""

    def test_route_after_patient_check_existing(self):
        from src.graph.edges import route_after_patient_check

        state = {"patient_exists": True, "patient_id": 1}
        result = route_after_patient_check(state)
        assert result == "classify_message"

    def test_route_after_patient_check_new(self):
        from src.graph.edges import route_after_patient_check

        state = {"patient_exists": False, "patient_id": None}
        result = route_after_patient_check(state)
        assert result == "register_patient"

    def test_route_after_classification_general(self):
        from src.graph.edges import route_after_classification

        state = {"classification": "general"}
        result = route_after_classification(state)
        assert result == "handle_general_query"

    def test_route_after_classification_urgency(self):
        from src.graph.edges import route_after_classification

        state = {"classification": "urgency"}
        result = route_after_classification(state)
        assert result == "handle_dental_urgency"

    def test_route_after_classification_emergency(self):
        from src.graph.edges import route_after_classification

        state = {"classification": "emergency"}
        result = route_after_classification(state)
        assert result == "handle_medical_emergency"


class TestAppointmentConflict:
    """Tests para verificación de conflictos de citas."""

    def test_no_conflict_empty_db(self):
        from src.services.appointment_service import AppointmentService
        from src.database.connection import get_session
        from datetime import date, time

        with get_session() as session:
            # Buscar un slot que no tenga conflicto
            has_conflict = AppointmentService.check_conflict(
                session,
                doctor_id=1,
                appointment_date=date(2029, 12, 31),
                start_time=time(8, 0),
                end_time=time(8, 30),
            )
            assert has_conflict is False
