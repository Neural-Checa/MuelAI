import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.database.connection import get_session, init_db, seed_demo_data
from src.graph.graph import create_dental_graph, get_initial_state
from src.services.appointment_service import AppointmentService
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService


# ── CSS Moderno ────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ────────────────────────────────────────── */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ───────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    padding: 0.6rem 1rem !important;
    font-size: 0.95rem !important;
    transition: border 0.3s, box-shadow 0.3s;
}
section[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,0.25) !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.2rem !important;
    transition: transform 0.2s, box-shadow 0.3s;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(14,165,233,0.35) !important;
}

/* ── Chat messages ─────────────────────────────────── */
.stChatMessage[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.8rem !important;
    animation: fadeInUp 0.35s ease;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Cards / Expanders ─────────────────────────────── */
.stExpander {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(8px);
}

/* ── Welcome screen ────────────────────────────────── */
.welcome-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 4rem 2rem;
    margin: 2rem auto;
    max-width: 600px;
}
.welcome-icon {
    font-size: 5rem;
    margin-bottom: 1rem;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}
.welcome-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}
.welcome-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    line-height: 1.6;
}

/* ── Status badges ─────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.badge-success { background: #065f46; color: #6ee7b7; }
.badge-warning { background: #713f12; color: #fcd34d; }
.badge-danger  { background: #7f1d1d; color: #fca5a5; }
.badge-info    { background: #1e3a5f; color: #7dd3fc; }

/* ── Header ────────────────────────────────────────── */
.app-header {
    padding: 1.2rem 0 0.5rem;
    margin-bottom: 0.5rem;
}
.app-header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0;
}
.app-header p {
    color: #94a3b8;
    margin: 0.25rem 0 0;
    font-size: 0.95rem;
}

/* ── Appointment card ──────────────────────────────── */
.appt-card {
    background: linear-gradient(135deg, rgba(14,165,233,0.12), rgba(99,102,241,0.12));
    border: 1px solid rgba(14,165,233,0.25);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.appt-card strong { color: #38bdf8; }

/* ── Chat input ────────────────────────────────────── */
.stChatInput > div {
    border-radius: 16px !important;
    border: 1px solid rgba(148,163,184,0.2) !important;
}
.stChatInput textarea {
    font-family: 'Inter', sans-serif !important;
}
</style>
"""


def initialize_app():
    """Inicializa la aplicación y la base de datos."""
    if "initialized" not in st.session_state:
        init_db()
        seed_demo_data()
        st.session_state.initialized = True


def initialize_session():
    """Inicializa el estado de la sesión de Streamlit."""
    if "graph" not in st.session_state:
        st.session_state.graph = create_dental_graph()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = None

    if "patient_dni" not in st.session_state:
        st.session_state.patient_dni = ""

    if "awaiting_human" not in st.session_state:
        st.session_state.awaiting_human = False

    if "messages_display" not in st.session_state:
        st.session_state.messages_display = []


def render_sidebar():
    """Renderiza el panel lateral con información y controles."""
    st.sidebar.markdown("## 🦷 MuelAI PRO")
    st.sidebar.caption("Sistema de Consultas Odontológicas")
    st.sidebar.markdown("---")

    # ── Identificación por DNI ─────────────────────────
    st.sidebar.markdown("#### 🪪 Identificación")
    dni = st.sidebar.text_input(
        "DNI del Paciente",
        value=st.session_state.patient_dni,
        placeholder="Ej: 76543210",
        max_chars=8,
        help="Ingresa tu DNI de 8 dígitos para identificarte",
    )

    if dni != st.session_state.patient_dni:
        st.session_state.patient_dni = dni
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.conversation_state = None
        st.session_state.messages_display = []
        st.rerun()

    st.sidebar.markdown("---")

    # ── Info del paciente ──────────────────────────────
    if st.session_state.patient_dni and len(st.session_state.patient_dni) == 8:
        with get_session() as session:
            patient = PatientService.get_patient_by_dni(
                session, st.session_state.patient_dni
            )
            if patient:
                st.sidebar.success(f"✅ Paciente: **{patient.name}**")

                history = PatientService.get_medical_history_summary(
                    session, patient.id
                )
                with st.sidebar.expander("📋 Historial Clínico"):
                    st.markdown(history)

                # Mostrar citas agendadas
                appointments = AppointmentService.get_patient_appointments(
                    session, patient.id
                )
                if appointments:
                    with st.sidebar.expander(f"📅 Citas Agendadas ({len(appointments)})"):
                        days_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                        for appt in appointments:
                            day_name = days_es[appt.appointment_date.weekday()]
                            st.markdown(
                                f"<div class='appt-card'>"
                                f"<strong>{day_name} {appt.appointment_date.strftime('%d/%m/%Y')}</strong><br/>"
                                f"🕐 {appt.start_time.strftime('%H:%M')} - {appt.end_time.strftime('%H:%M')}<br/>"
                                f"👨‍⚕️ Dr. ID {appt.doctor_id}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
            else:
                st.sidebar.info("🆕 Paciente nuevo — se registrará al enviar un mensaje")
    elif st.session_state.patient_dni:
        st.sidebar.warning("⚠️ El DNI debe tener 8 dígitos")

    st.sidebar.markdown("---")

    # ── Estado del sistema ─────────────────────────────
    st.sidebar.markdown("#### 📊 Estado")

    if st.session_state.conversation_state:
        state = st.session_state.conversation_state
        classification = state.get("classification")

        if classification:
            classification_labels = {
                "general": ("Consulta General", "badge-info", "🟢"),
                "urgency": ("Urgencia Dental", "badge-warning", "🟡"),
                "emergency": ("Emergencia Médica", "badge-danger", "🔴"),
            }
            label, badge_cls, icon = classification_labels.get(
                classification, (classification, "badge-info", "⚪")
            )
            st.sidebar.markdown(
                f"{icon} <span class='badge {badge_cls}'>{label}</span>",
                unsafe_allow_html=True,
            )

        if state.get("assigned_doctor"):
            doc = state["assigned_doctor"]
            st.sidebar.success(f"👨‍⚕️ Asignado: **{doc['doctor_name']}**")

    st.sidebar.markdown("---")

    # ── Admin panel ────────────────────────────────────
    st.sidebar.markdown("#### ⚙️ Administración")

    with st.sidebar.expander("Gestionar Doctores"):
        with get_session() as session:
            doctors = DoctorService.get_all_doctors(session)

            for doc in doctors:
                col1, col2 = st.columns([3, 1])
                with col1:
                    status = "🟢" if doc.is_available else "🔴"
                    st.markdown(f"{status} **{doc.doctor_name}**")
                    st.caption(doc.specialty)

                with col2:
                    if st.button(
                        "Toggle",
                        key=f"toggle_{doc.doctor_id}",
                        help="Cambiar disponibilidad",
                    ):
                        DoctorService.set_doctor_availability(
                            session, doc.doctor_id, not doc.is_available
                        )
                        session.commit()
                        st.rerun()

    # Mostrar horarios
    with st.sidebar.expander("📅 Horarios de Doctores"):
        with get_session() as session:
            doctors = DoctorService.get_all_doctors(session)
            days_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            for doc in doctors:
                st.markdown(f"**{doc.doctor_name}** — {doc.specialty}")
                schedules = AppointmentService.get_doctor_schedule(session, doc.doctor_id)
                if schedules:
                    for sched in schedules:
                        day_name = days_es[sched.day_of_week]
                        st.caption(
                            f"  {day_name}: {sched.start_time.strftime('%H:%M')} - {sched.end_time.strftime('%H:%M')}"
                        )
                else:
                    st.caption("  Sin horario asignado")
                st.markdown("")

    if st.sidebar.button("🔄 Nueva Conversación", type="secondary", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.conversation_state = None
        st.session_state.messages_display = []
        st.session_state.awaiting_human = False
        st.rerun()


def process_message(user_input: str):
    """Procesa un mensaje del usuario a través del grafo."""
    if not st.session_state.patient_dni or len(st.session_state.patient_dni) != 8:
        st.warning("Por favor, ingresa tu DNI de 8 dígitos en el panel lateral.")
        return

    st.session_state.messages_display.append({"role": "user", "content": user_input})

    if st.session_state.conversation_state is None:
        initial_state = get_initial_state(st.session_state.patient_dni)
        initial_state["messages"] = [HumanMessage(content=user_input)]
    else:
        initial_state = st.session_state.conversation_state.copy()
        initial_state["messages"] = initial_state["messages"] + [
            HumanMessage(content=user_input)
        ]

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    try:
        result = st.session_state.graph.invoke(initial_state, config)

        st.session_state.conversation_state = result

        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage):
                already_displayed = any(
                    m["content"] == msg.content and m["role"] == "assistant"
                    for m in st.session_state.messages_display
                )
                if not already_displayed:
                    st.session_state.messages_display.append(
                        {"role": "assistant", "content": msg.content}
                    )

        if result.get("awaiting_human"):
            st.session_state.awaiting_human = True

    except Exception as e:
        error_msg = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo."
        st.session_state.messages_display.append(
            {"role": "assistant", "content": error_msg}
        )
        st.error(f"Error: {str(e)}")


def render_welcome():
    """Pantalla de bienvenida cuando no hay DNI."""
    st.markdown(
        """
        <div class="welcome-container">
            <div class="welcome-icon">🦷</div>
            <div class="welcome-title">MuelAI PRO</div>
            <div class="welcome-subtitle">
                Bienvenido al asistente virtual de consultas odontológicas.<br/>
                Para comenzar, ingresa tu <strong>DNI de 8 dígitos</strong> en el panel lateral izquierdo.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat():
    """Renderiza la interfaz de chat."""
    # ── Gate DNI: si no hay DNI válido, mostrar bienvenida ─────
    if not st.session_state.patient_dni or len(st.session_state.patient_dni) != 8:
        render_welcome()
        return

    # ── Header ─────────────────────────────────────────────────
    st.markdown(
        """
        <div class="app-header">
            <h1>🦷 Asistente Dental Virtual</h1>
            <p>Describe tus síntomas o consulta y te ayudaremos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Chat container ─────────────────────────────────────────
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages_display:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if st.session_state.awaiting_human:
        st.warning(
            "⏳ Tu caso está siendo revisado por nuestro equipo. "
            "Por favor, espera mientras un operador te asiste."
        )

        if st.button("Verificar disponibilidad de doctores"):
            with get_session() as session:
                doctors = DoctorService.get_available_doctors(session)
                if doctors:
                    st.session_state.awaiting_human = False
                    st.info("¡Hay doctores disponibles! Procesando tu caso...")
                    st.rerun()
                else:
                    st.info("Aún no hay doctores disponibles. Por favor, espera.")

    user_input = st.chat_input(
        "Escribe tu consulta aquí...",
        disabled=st.session_state.awaiting_human,
    )

    if user_input:
        process_message(user_input)
        st.rerun()


def main():
    """Función principal de la aplicación."""
    st.set_page_config(
        page_title="MuelAI PRO — Asistente Dental",
        page_icon="🦷",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inyectar CSS moderno
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    initialize_app()
    initialize_session()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
