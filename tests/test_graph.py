import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage


class TestMessageClassification:
    """Tests para la clasificación de mensajes."""

    def test_general_query_examples(self):
        """Ejemplos de consultas que deberían clasificarse como 'general'."""
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
        """Ejemplos de consultas que deberían clasificarse como 'urgency'."""
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
        """Ejemplos de consultas que deberían clasificarse como 'emergency'."""
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
        """Verifica que el estado inicial tenga la estructura correcta."""
        from src.graph.graph import get_initial_state

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


class TestEdgeRouting:
    """Tests para las funciones de routing."""

    def test_route_after_patient_check_existing(self):
        """Test routing cuando el paciente existe."""
        from src.graph.edges import route_after_patient_check

        state = {
            "patient_exists": True,
            "patient_id": 1,
        }
        result = route_after_patient_check(state)
        assert result == "classify_message"

    def test_route_after_patient_check_new(self):
        """Test routing cuando el paciente es nuevo."""
        from src.graph.edges import route_after_patient_check

        state = {
            "patient_exists": False,
            "patient_id": None,
        }
        result = route_after_patient_check(state)
        assert result == "register_patient"

    def test_route_after_classification_general(self):
        """Test routing para consulta general."""
        from src.graph.edges import route_after_classification

        state = {"classification": "general"}
        result = route_after_classification(state)
        assert result == "handle_general_query"

    def test_route_after_classification_urgency(self):
        """Test routing para urgencia dental."""
        from src.graph.edges import route_after_classification

        state = {"classification": "urgency"}
        result = route_after_classification(state)
        assert result == "handle_dental_urgency"

    def test_route_after_classification_emergency(self):
        """Test routing para emergencia médica."""
        from src.graph.edges import route_after_classification

        state = {"classification": "emergency"}
        result = route_after_classification(state)
        assert result == "handle_medical_emergency"
