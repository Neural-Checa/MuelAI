from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from src.agents.classifier import MessageClassifier
from src.agents.responder import DentalResponder
from src.database.connection import get_session
from src.graph.state import ConversationState
from src.services.appointment_service import AppointmentService
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
                    f"¡Bienvenido/a a MuelAI!"
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
    """Maneja urgencias dentales: obtiene doctores y pasa a agendar cita."""
    patient_name = state.get("patient_name", "Paciente")
    messages = state.get("messages", [])
    last_human_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

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

    if doctors_list:
        responder = DentalResponder()
        response = responder.respond_urgency(
            user_message=last_human_message,
            available_doctors=doctors_list,
            patient_name=patient_name,
        )
        return {
            **state,
            "available_doctors": doctors_list,
            "awaiting_human": False,
            "from_check_availability": False,
            "messages": state["messages"] + [AIMessage(content=response)],
        }
    else:
        initial_response = (
            f"Entiendo que tienes una urgencia dental, {patient_name}. "
            "En este momento no hay doctores disponibles. "
            "Por favor, haz clic en 'Verificar disponibilidad' cuando esté listo."
        )
        human_input = interrupt(
            {
                "type": "urgency_no_doctors",
                "message": f"URGENCIA DENTAL - Paciente: {patient_name}\nMensaje: {last_human_message}",
                "patient_phone": state.get("patient_phone"),
                "required_action": "update_availability",
            }
        )
        if human_input and human_input.get("retry"):
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
            if doctors_list:
                return {
                    **state,
                    "available_doctors": doctors_list,
                    "awaiting_human": False,
                    "from_check_availability": False,
                }
        return {
            **state,
            "available_doctors": [],
            "awaiting_human": True,
            "from_check_availability": False,
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
        "from_check_availability": True,
    }


def select_appointment_slot(state: ConversationState) -> ConversationState:
    """
    Human-in-the-loop: muestra slots disponibles y espera que el paciente seleccione.
    Cuando se resume con human_response (slot seleccionado), crea la cita.
    """
    patient_id = state.get("patient_id")
    patient_name = state.get("patient_name", "Paciente")

    if not patient_id:
        return {
            **state,
            "messages": state["messages"]
            + [AIMessage(content="Necesito tu número de teléfono para agendar. Indícalo en el panel lateral.")],
        }

    available_doctors = state.get("available_doctors", [])
    doctor_ids = [d["doctor_id"] for d in available_doctors] if available_doctors else None

    with get_session() as session:
        slots = AppointmentService.get_available_slots(session, doctor_ids)

    if not slots:
        return {
            **state,
            "messages": state["messages"]
            + [
                AIMessage(
                    content="Lo siento, no hay horarios disponibles en este momento. "
                    "Por favor, intenta más tarde o contacta con nosotros."
                )
            ],
            "available_slots": [],
        }

    selected = interrupt(
        {
            "type": "slot_selection",
            "slots": slots,
            "message": "Selecciona un horario disponible para tu cita",
        }
    )

    slot_id = None
    if isinstance(selected, dict):
        slot_id = selected.get("slot_id")
    elif isinstance(selected, str):
        slot_id = selected

    if slot_id:
        try:
            parts = slot_id.split("|")
            if len(parts) == 2:
                doctor_id = int(parts[0])
                scheduled_at = datetime.fromisoformat(parts[1])

                with get_session() as session:
                    from src.database.models import Doctor as DoctorModel

                    appointment = AppointmentService.create_appointment(
                        session, patient_id, doctor_id, scheduled_at
                    )
                    appointment_id = appointment.id
                    doctor_obj = (
                        session.query(DoctorModel)
                        .filter(DoctorModel.id == doctor_id)
                        .first()
                    )
                    doctor_name = doctor_obj.name if doctor_obj else "Doctor"

                display_time = scheduled_at.strftime("%d/%m/%Y a las %H:%M")
                response = (
                    f"¡Cita agendada exitosamente, {patient_name}! "
                    f"Tu cita queda programada para el {display_time} "
                    f"con {doctor_name}. Te esperamos."
                )
                return {
                    **state,
                    "appointment_confirmed": {
                        "id": appointment_id,
                        "scheduled_at": scheduled_at.isoformat(),
                        "doctor_name": doctor_name,
                    },
                    "messages": state["messages"] + [AIMessage(content=response)],
                }
        except (ValueError, IndexError):
            pass

    return {
        **state,
        "messages": state["messages"]
        + [
            AIMessage(
                content="Lo siento, hubo un error al agendar. Por favor, selecciona un horario de la lista."
            )
        ],
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
