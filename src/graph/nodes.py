from datetime import date, datetime, timedelta, time

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from src.agents.classifier import MessageClassifier
from src.agents.responder import DentalResponder
from src.database.connection import get_session, CLINIC_NAME, CLINIC_PHONE, CLINIC_WEBSITE
from src.graph.state import ConversationState
from src.services.appointment_service import AppointmentService
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService

DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def verify_patient(state: ConversationState) -> ConversationState:
    """Verifica si el paciente existe en el sistema por DNI."""
    patient_dni = state.get("patient_dni")

    if not patient_dni:
        return {
            **state,
            "patient_exists": False,
            "patient_id": None,
            "patient_name": None,
        }

    with get_session() as session:
        patient = PatientService.get_patient_by_dni(session, patient_dni)

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
    """Registra un nuevo paciente usando su DNI."""
    patient_dni = state.get("patient_dni")

    if not patient_dni:
        return {
            **state,
            "messages": state["messages"]
            + [
                AIMessage(
                    content="Para poder atenderte mejor, necesito tu DNI. "
                    "Por favor, indícalo en el panel lateral."
                )
            ],
        }

    with get_session() as session:
        patient = PatientService.create_patient(
            session,
            dni=patient_dni,
            name=f"Paciente {patient_dni}",
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
                    content=f"Te he registrado como nuevo paciente con DNI {patient_dni}. "
                    f"¡Bienvenido/a a {CLINIC_NAME}!"
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


def _build_available_slots(session, doctors_list: list[dict], max_slots: int = 6) -> list[dict]:
    """Construye la lista de slots disponibles para los doctores dados."""
    today = date.today()
    all_slots = []

    for doc_info in doctors_list:
        doctor_id = doc_info["doctor_id"]
        doctor_name = doc_info["doctor_name"]
        specialty = doc_info["specialty"]

        # Buscar slots disponibles en los próximos 7 días
        for day_offset in range(8):
            check_date = today + timedelta(days=day_offset)
            if check_date == today and datetime.now().hour >= 17:
                continue  # Si ya es tarde hoy, saltar a mañana

            day_of_week = check_date.weekday()
            schedules = AppointmentService.get_doctor_schedule(session, doctor_id)
            day_schedules = [s for s in schedules if s.day_of_week == day_of_week]

            for sched in day_schedules:
                current = sched.start_time
                while True:
                    slot_end_dt = datetime.combine(check_date, current) + timedelta(minutes=30)
                    slot_end = slot_end_dt.time()

                    if slot_end > sched.end_time:
                        break

                    if not AppointmentService.check_conflict(
                        session, doctor_id, check_date, current, slot_end
                    ):
                        day_name = DAYS_ES[check_date.weekday()]
                        all_slots.append({
                            "doctor_id": doctor_id,
                            "doctor_name": doctor_name,
                            "specialty": specialty,
                            "date": check_date.isoformat(),
                            "date_display": f"{day_name} {check_date.strftime('%d/%m/%Y')}",
                            "start_time": current.strftime("%H:%M"),
                            "end_time": slot_end.strftime("%H:%M"),
                        })
                        if len(all_slots) >= max_slots:
                            return all_slots

                    current = slot_end

    return all_slots


def handle_dental_urgency(state: ConversationState) -> ConversationState:
    """
    Maneja urgencias dentales:
    - Si hay doctores disponibles → muestra horarios disponibles para que el paciente elija
    - Si NO hay doctores → HITL (human-in-the-loop) para que un operador active doctores
    """
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

    if doctors_list:
        # Construir la lista de slots disponibles
        with get_session() as session:
            slots = _build_available_slots(session, doctors_list, max_slots=8)

        if slots:
            # Formar mensaje con los horarios disponibles
            slots_text = f"🏥 **{CLINIC_NAME}**\n"
            slots_text += f"📞 {CLINIC_PHONE} | 🌐 {CLINIC_WEBSITE}\n\n"
            slots_text += f"Entiendo tu urgencia, {patient_name}. "
            slots_text += "He encontrado los siguientes horarios disponibles para atenderte:\n\n"

            for i, slot in enumerate(slots, 1):
                slots_text += (
                    f"**{i}.** 👨‍⚕️ {slot['doctor_name']} ({slot['specialty']})\n"
                    f"   📅 {slot['date_display']} — 🕐 {slot['start_time']} a {slot['end_time']}\n\n"
                )

            slots_text += "**Selecciona un horario en el panel que aparece debajo del chat** para confirmar tu cita."

            return {
                **state,
                "available_doctors": doctors_list,
                "available_slots": slots,
                "awaiting_human": False,
                "messages": state["messages"] + [AIMessage(content=slots_text)],
            }
        else:
            no_slots_msg = (
                f"Entiendo tu urgencia, {patient_name}. "
                "No encontramos horarios disponibles en los próximos días. "
                f"Por favor, llama a {CLINIC_PHONE} para coordinar una cita de emergencia."
            )
            return {
                **state,
                "available_doctors": doctors_list,
                "available_slots": [],
                "messages": state["messages"] + [AIMessage(content=no_slots_msg)],
            }
    else:
        # No hay doctores disponibles → HITL
        initial_response = (
            f"Entiendo que tienes una urgencia dental, {patient_name}. "
            "En este momento no hay doctores disponibles, pero estoy notificando "
            "a nuestro equipo para que te asistan lo antes posible. "
            "Por favor, mantente en línea.\n\n"
            f"Si es una emergencia inmediata, llama al 📞 **{CLINIC_PHONE}**."
        )

        human_input = interrupt(
            {
                "type": "urgency_no_doctors",
                "message": f"URGENCIA DENTAL - Paciente: {patient_name}\n"
                f"Mensaje: {last_human_message}\n\n"
                "No hay doctores disponibles. Por favor, actualice la disponibilidad "
                "o asigne un doctor manualmente.",
                "patient_dni": state.get("patient_dni"),
                "required_action": "update_availability",
            }
        )

        return {
            **state,
            "available_doctors": [],
            "available_slots": [],
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
    """Conecta al paciente con un doctor disponible para HITL chat."""
    available_doctors = state.get("available_doctors", [])
    patient_name = state.get("patient_name", "Paciente")

    if not available_doctors:
        return {
            **state,
            "messages": state["messages"]
            + [
                AIMessage(
                    content="Lo siento, en este momento no hay doctores disponibles. "
                    f"Por favor, llame al {CLINIC_PHONE} para asistencia."
                )
            ],
        }

    selected_doctor = available_doctors[0]

    response = (
        f"¡Buenas noticias, {patient_name}! "
        f"**{selected_doctor['doctor_name']}** ({selected_doctor['specialty']}) "
        f"se ha unido al chat para atender tu urgencia.\n\n"
        f"El doctor puede revisar tu historial y comunicarse contigo directamente "
        f"a través de este chat. Por favor, describe tus síntomas con detalle."
    )

    return {
        **state,
        "assigned_doctor": selected_doctor,
        "doctor_in_chat": True,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def schedule_appointment(state: ConversationState) -> ConversationState:
    """Agenda automáticamente una cita con el doctor asignado (post HITL), verificando conflictos."""
    assigned_doctor = state.get("assigned_doctor")
    patient_id = state.get("patient_id")
    patient_name = state.get("patient_name", "Paciente")

    if not assigned_doctor or not patient_id:
        return state

    doctor_id = assigned_doctor["doctor_id"]
    doctor_name = assigned_doctor["doctor_name"]

    with get_session() as session:
        today = date.today()
        slot = AppointmentService.get_next_available_slot(
            session, doctor_id, today, duration_minutes=30
        )

        if slot:
            appt_date, start_time, end_time = slot
            appointment, error = AppointmentService.create_appointment(
                session,
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_date=appt_date,
                start_time=start_time,
                end_time=end_time,
                reason="Urgencia dental — derivación por HITL",
            )

            if appointment:
                day_name = DAYS_ES[appt_date.weekday()]
                appt_info = (
                    f"📅 **Cita agendada exitosamente**\n\n"
                    f"- **Clínica:** {CLINIC_NAME}\n"
                    f"- **Doctor:** {doctor_name}\n"
                    f"- **Fecha:** {day_name} {appt_date.strftime('%d/%m/%Y')}\n"
                    f"- **Hora:** {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n"
                    f"- **Motivo:** Urgencia dental\n\n"
                    f"📞 {CLINIC_PHONE} | 🌐 {CLINIC_WEBSITE}\n"
                    f"Por favor, llegue 10 minutos antes de su cita."
                )
                session.commit()
                return {
                    **state,
                    "appointment_info": appt_info,
                    "messages": state["messages"] + [AIMessage(content=appt_info)],
                }
            else:
                err_msg = f"No se pudo agendar la cita: {error}"
                return {
                    **state,
                    "messages": state["messages"] + [AIMessage(content=err_msg)],
                }
        else:
            no_slot_msg = (
                f"{patient_name}, no encontramos horarios disponibles con {doctor_name} "
                f"en las próximas 2 semanas. Llame al {CLINIC_PHONE} para coordinar."
            )
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content=no_slot_msg)],
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

    emergency_info = f"""

---
**🏥 {CLINIC_NAME}**
📞 {CLINIC_PHONE} | 🌐 {CLINIC_WEBSITE}

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
