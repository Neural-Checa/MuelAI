from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from src.agents.classifier import MessageClassifier
from src.agents.responder import DentalResponder
from src.database.connection import get_session
from src.graph.state import ConversationState
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService


def verify_patient(state: ConversationState) -> ConversationState:
    """Verifica si el paciente existe en el sistema."""
    patient_phone = state.get("patient_phone")

    if not patient_phone:
        return {
            **state,
            "patient_exists": False,
            "patient_id": None,
            "patient_name": None,
        }

    with get_session() as session:
        patient = PatientService.get_patient_by_phone(session, patient_phone)

        if patient:
            return {
                **state,
                "patient_exists": True,
                "patient_id": patient.id,
                "patient_name": patient.name,
            }
        else:
            return {
                **state,
                "patient_exists": False,
                "patient_id": None,
                "patient_name": None,
            }


def register_patient(state: ConversationState) -> ConversationState:
    """Registra un nuevo paciente (simplificado - usa el teléfono como nombre temporal)."""
    patient_phone = state.get("patient_phone")

    if not patient_phone:
        return {
            **state,
            "messages": state["messages"]
            + [
                AIMessage(
                    content="Para poder atenderte mejor, necesito tu número de teléfono. "
                    "Por favor, indícalo en el panel lateral."
                )
            ],
        }

    with get_session() as session:
        patient = PatientService.create_patient(
            session,
            name=f"Paciente {patient_phone}",
            phone=patient_phone,
        )
        session.commit()

        return {
            **state,
            "patient_exists": True,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "messages": state["messages"]
            + [
                AIMessage(
                    content=f"Te he registrado como nuevo paciente. "
                    f"¡Bienvenido/a a nuestra clínica dental!"
                )
            ],
        }


def classify_message(state: ConversationState) -> ConversationState:
    """Clasifica el mensaje del paciente usando el LLM."""
    messages = state.get("messages", [])

    last_human_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    if not last_human_message:
        return {**state, "classification": "general"}

    classifier = MessageClassifier()
    classification = classifier.classify(last_human_message)

    return {**state, "classification": classification}


def handle_general_query(state: ConversationState) -> ConversationState:
    """Maneja consultas generales consultando el historial y generando respuesta."""
    patient_id = state.get("patient_id")
    patient_name = state.get("patient_name", "Paciente")

    medical_history = "No hay historial médico disponible."
    if patient_id:
        with get_session() as session:
            medical_history = PatientService.get_medical_history_summary(
                session, patient_id
            )

    messages = state.get("messages", [])
    last_human_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    responder = DentalResponder()
    response = responder.respond_general_query(
        user_message=last_human_message,
        medical_history=medical_history,
        patient_name=patient_name,
        conversation_history=messages,
    )

    return {
        **state,
        "medical_history": medical_history,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def handle_dental_urgency(state: ConversationState) -> ConversationState:
    """Maneja urgencias dentales con human-in-the-loop."""
    patient_name = state.get("patient_name", "Paciente")

    with get_session() as session:
        available_doctors = DoctorService.get_available_doctors(session)
        doctors_list = [
            {
                "doctor_id": doc.doctor_id,
                "doctor_name": doc.doctor_name,
                "specialty": doc.specialty,
            }
            for doc in available_doctors
        ]

    messages = state.get("messages", [])
    last_human_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    responder = DentalResponder()

    if doctors_list:
        response = responder.respond_urgency(
            user_message=last_human_message,
            available_doctors=doctors_list,
            patient_name=patient_name,
        )

        return {
            **state,
            "available_doctors": doctors_list,
            "awaiting_human": False,
            "messages": state["messages"] + [AIMessage(content=response)],
        }
    else:
        initial_response = (
            f"Entiendo que tienes una urgencia dental, {patient_name}. "
            "En este momento no hay doctores disponibles, pero estoy notificando "
            "a nuestro equipo para que te asistan lo antes posible. "
            "Por favor, mantente en línea."
        )

        human_input = interrupt(
            {
                "type": "urgency_no_doctors",
                "message": f"URGENCIA DENTAL - Paciente: {patient_name}\n"
                f"Mensaje: {last_human_message}\n\n"
                "No hay doctores disponibles. Por favor, actualice la disponibilidad "
                "o asigne un doctor manualmente.",
                "patient_phone": state.get("patient_phone"),
                "required_action": "update_availability",
            }
        )

        return {
            **state,
            "available_doctors": [],
            "awaiting_human": True,
            "human_response": human_input,
            "messages": state["messages"] + [AIMessage(content=initial_response)],
        }


def check_doctor_availability(state: ConversationState) -> ConversationState:
    """Verifica la disponibilidad de doctores después de intervención humana."""
    with get_session() as session:
        available_doctors = DoctorService.get_available_doctors(session)
        doctors_list = [
            {
                "doctor_id": doc.doctor_id,
                "doctor_name": doc.doctor_name,
                "specialty": doc.specialty,
            }
            for doc in available_doctors
        ]

    return {
        **state,
        "available_doctors": doctors_list,
        "awaiting_human": False,
    }


def connect_doctor(state: ConversationState) -> ConversationState:
    """Conecta al paciente con un doctor disponible."""
    available_doctors = state.get("available_doctors", [])
    patient_name = state.get("patient_name", "Paciente")

    if not available_doctors:
        return {
            **state,
            "messages": state["messages"]
            + [
                AIMessage(
                    content="Lo siento, en este momento no hay doctores disponibles. "
                    "Por favor, espere mientras nuestro equipo gestiona su caso."
                )
            ],
        }

    selected_doctor = available_doctors[0]

    response = (
        f"¡Buenas noticias, {patient_name}! "
        f"Te he conectado con {selected_doctor['doctor_name']} "
        f"({selected_doctor['specialty']}). "
        f"El doctor se unirá a este chat en breve para atender tu urgencia."
    )

    return {
        **state,
        "assigned_doctor": selected_doctor,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def handle_medical_emergency(state: ConversationState) -> ConversationState:
    """Maneja emergencias médicas proporcionando contactos de emergencia."""
    patient_name = state.get("patient_name", "Paciente")

    messages = state.get("messages", [])
    last_human_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    responder = DentalResponder()
    response = responder.respond_emergency(
        user_message=last_human_message,
        patient_name=patient_name,
    )

    emergency_info = """

---
**CONTACTOS DE EMERGENCIA:**
- **Emergencias (SAMU):** 106
- **Bomberos:** 116
- **Policía Nacional:** 105
- **Cruz Roja:** (01) 266-0481

**⚠️ Si su vida está en peligro, llame al 106 INMEDIATAMENTE.**
---
"""

    full_response = response + emergency_info

    return {
        **state,
        "emergency_contacts_provided": True,
        "messages": state["messages"] + [AIMessage(content=full_response)],
    }
