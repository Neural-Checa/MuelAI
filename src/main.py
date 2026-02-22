import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.database.connection import get_session, init_db, seed_demo_data
from src.graph.graph import create_dental_graph, get_initial_state
from src.services.appointment_service import AppointmentService
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService

# Branding
BRAND_NAME = "MuelAI"


def inject_custom_css():
    """Inyecta estilos CSS modernos."""
    st.markdown(
        """
    <style>
        /* Variables de tema */
        :root {
            --primary: #0d9488;
            --primary-dark: #0f766e;
            --primary-light: #14b8a6;
            --accent: #f59e0b;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
        }

        /* Ocultar elementos por defecto de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Estilo general */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
            border-right: 1px solid rgba(20, 184, 166, 0.2);
        }

        [data-testid="stSidebar"] .stMarkdown h1,
        [data-testid="stSidebar"] .stMarkdown h2 {
            color: #14b8a6 !important;
            font-weight: 700;
        }

        /* Brand header */
        .brand-header {
            background: linear-gradient(90deg, #0d9488, #14b8a6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin-bottom: 0;
        }

        /* Chat messages */
        [data-testid="stChatMessage"] {
            background: rgba(30, 41, 59, 0.8) !important;
            border-radius: 16px;
            padding: 1rem 1.25rem !important;
            margin: 0.5rem 0;
            border: 1px solid rgba(20, 184, 166, 0.15);
            backdrop-filter: blur(8px);
        }

        [data-testid="stChatMessage"] p {
            color: #e2e8f0 !important;
        }

        /* Input */
        .stChatInput {
            background: rgba(30, 41, 59, 0.9) !important;
            border-radius: 24px !important;
            border: 1px solid rgba(20, 184, 166, 0.3) !important;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #0d9488, #14b8a6) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(20, 184, 166, 0.4);
        }

        /* Expanders */
        [data-testid="stExpander"] {
            background: rgba(30, 41, 59, 0.6);
            border-radius: 12px;
            border: 1px solid rgba(20, 184, 166, 0.2);
        }

        /* Hero section */
        .hero-title {
            font-size: 2.25rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.5rem;
        }

        .hero-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
        }

        /* Slot buttons */
        div[data-testid="column"] > div > button {
            background: linear-gradient(135deg, #1e293b, #334155) !important;
            border: 2px solid rgba(20, 184, 166, 0.4) !important;
            color: #14b8a6 !important;
        }

        div[data-testid="column"] > div > button:hover {
            border-color: #14b8a6 !important;
            background: rgba(20, 184, 166, 0.2) !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


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

    if "patient_phone" not in st.session_state:
        st.session_state.patient_phone = ""

    if "awaiting_human" not in st.session_state:
        st.session_state.awaiting_human = False

    if "messages_display" not in st.session_state:
        st.session_state.messages_display = []

    if "pending_interrupt" not in st.session_state:
        st.session_state.pending_interrupt = None


def render_sidebar():
    """Renderiza el panel lateral con información y controles."""
    st.sidebar.markdown(
        f'<p class="brand-header">{BRAND_NAME}</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Tu asistente dental inteligente")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Identificación del Paciente")
    phone = st.sidebar.text_input(
        "Número de Teléfono",
        value=st.session_state.patient_phone,
        placeholder="Ej: 999888777",
        help="Ingresa tu número de teléfono para identificarte",
    )

    if phone != st.session_state.patient_phone:
        st.session_state.patient_phone = phone
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.conversation_state = None
        st.session_state.messages_display = []
        st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.patient_phone:
        with get_session() as session:
            patient = PatientService.get_patient_by_phone(
                session, st.session_state.patient_phone
            )
            if patient:
                st.sidebar.success(f"Paciente: {patient.name}")

                appointments = AppointmentService.get_patient_appointments(
                    session, patient.id
                )
                with st.sidebar.expander("📅 Mis Citas Agendadas"):
                    if appointments:
                        for apt in appointments[:5]:
                            dt = apt.scheduled_at
                            dt_str = (
                                dt.strftime("%d/%m/%Y %H:%M")
                                if hasattr(dt, "strftime")
                                else str(dt)
                            )
                            st.markdown(
                                f"- **{dt_str}** con {apt.doctor.name} ({apt.status})"
                            )
                        if len(appointments) > 5:
                            st.caption(f"+ {len(appointments) - 5} más")
                    else:
                        st.caption("No tienes citas agendadas")

                history = PatientService.get_medical_history_summary(
                    session, patient.id
                )
                with st.sidebar.expander("Ver Historial Clínico"):
                    st.markdown(history)
            else:
                st.sidebar.info("Paciente no registrado (se creará automáticamente)")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Estado del Sistema")

    if st.session_state.conversation_state:
        state = st.session_state.conversation_state
        classification = state.get("classification")

        if classification:
            classification_labels = {
                "general": "Consulta General",
                "urgency": "Urgencia Dental",
                "emergency": "Emergencia Médica",
            }
            classification_colors = {
                "general": "🟢",
                "urgency": "🟡",
                "emergency": "🔴",
            }
            label = classification_labels.get(classification, classification)
            color = classification_colors.get(classification, "⚪")
            st.sidebar.markdown(f"**Clasificación:** {color} {label}")

        if state.get("assigned_doctor"):
            doc = state["assigned_doctor"]
            st.sidebar.success(f"Doctor asignado: {doc['doctor_name']}")

        if state.get("appointment_confirmed"):
            apt = state["appointment_confirmed"]
            st.sidebar.success(
                f"✅ Cita agendada: {apt.get('doctor_name', 'Doctor')}"
            )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Panel de Administración")

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
                        "Cambiar",
                        key=f"toggle_{doc.doctor_id}",
                        help="Activar/Desactivar disponibilidad",
                    ):
                        DoctorService.set_doctor_availability(
                            session, doc.doctor_id, not doc.is_available
                        )
                        session.commit()
                        st.rerun()

    if st.sidebar.button("Nueva Conversación", type="secondary"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.conversation_state = None
        st.session_state.messages_display = []
        st.session_state.awaiting_human = False
        st.session_state.pending_interrupt = None
        st.rerun()


def resume_graph(resume_value):
    """Reanuda el grafo tras un interrupt con el valor proporcionado."""
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    result = st.session_state.graph.invoke(Command(resume=resume_value), config)
    st.session_state.conversation_state = result
    st.session_state.pending_interrupt = None

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


def process_message(user_input: str):
    """Procesa un mensaje del usuario a través del grafo."""
    st.session_state.messages_display.append({"role": "user", "content": user_input})

    if not st.session_state.patient_phone:
        st.session_state.messages_display.append(
            {
                "role": "assistant",
                "content": "Para poder atenderte, necesito que ingreses tu **número de teléfono** en el panel lateral (izquierda). "
                "Es necesario para identificarte y gestionar tu consulta.",
            }
        )
        return

    if st.session_state.conversation_state is None:
        initial_state = get_initial_state(st.session_state.patient_phone)
        initial_state["messages"] = [HumanMessage(content=user_input)]
    else:
        initial_state = st.session_state.conversation_state.copy()
        initial_state["messages"] = initial_state["messages"] + [
            HumanMessage(content=user_input)
        ]

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    try:
        with st.spinner("Procesando tu consulta..."):
            result = st.session_state.graph.invoke(initial_state, config)

        st.session_state.conversation_state = result

        if "__interrupt__" in result and result["__interrupt__"]:
            st.session_state.pending_interrupt = result["__interrupt__"]
            st.session_state.awaiting_human = True
        else:
            st.session_state.pending_interrupt = None

        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage):
                content = (msg.content or "").strip()
                if content:
                    already_displayed = any(
                        m.get("content") == content and m.get("role") == "assistant"
                        for m in st.session_state.messages_display
                    )
                    if not already_displayed:
                        st.session_state.messages_display.append(
                            {"role": "assistant", "content": content}
                        )

        if result.get("awaiting_human"):
            st.session_state.awaiting_human = True

    except Exception as e:
        error_msg = (
            "Lo siento, ocurrió un error al procesar tu mensaje. "
            "Verifica que tu API Key de Google Gemini esté configurada correctamente en el archivo .env"
        )
        st.session_state.messages_display.append(
            {"role": "assistant", "content": error_msg}
        )
        st.error(f"Error: {str(e)}")


def render_chat():
    """Renderiza la interfaz de chat."""
    if not st.session_state.patient_phone:
        st.info(
            "👆 **Ingresa tu número de teléfono** en el panel lateral para comenzar la conversación."
        )

    st.markdown(
        f'<p class="hero-title">Hola, ¿en qué puedo ayudarte?</p>'
        f'<p class="hero-subtitle">Describe tus síntomas o consulta y te atenderemos. '
        f'Urgencias, citas y dudas generales.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages_display:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if st.session_state.awaiting_human and st.session_state.pending_interrupt:
        interrupt_list = st.session_state.pending_interrupt
        if interrupt_list:
            first_interrupt = interrupt_list[0]
            interrupt_value = getattr(first_interrupt, "value", first_interrupt)

            if isinstance(interrupt_value, dict):
                if interrupt_value.get("type") == "slot_selection":
                    slots = interrupt_value.get("slots", [])
                    st.markdown("**Selecciona un horario disponible para tu cita:**")
                    cols = st.columns(3)
                    for i, slot in enumerate(slots):
                        with cols[i % 3]:
                            if st.button(
                                f"📅 {slot.get('display', slot)} - {slot.get('doctor_name', '')}",
                                key=f"slot_{slot.get('slot_id', i)}",
                            ):
                                resume_graph({"slot_id": slot["slot_id"]})
                                st.rerun()

                elif interrupt_value.get("type") == "urgency_no_doctors":
                    st.warning(
                        "⏳ No hay doctores disponibles en este momento. "
                        "Por favor, espera o verifica la disponibilidad."
                    )
                    if st.button("Verificar disponibilidad de doctores"):
                        resume_graph({"retry": True})
                        st.rerun()
            else:
                st.warning(
                    "⏳ Tu caso está siendo revisado. "
                    "Por favor, espera mientras un operador te asiste."
                )
    elif st.session_state.awaiting_human:
        st.warning(
            "⏳ Tu caso está siendo revisado. "
            "Por favor, espera mientras un operador te asiste."
        )

    user_input = st.chat_input(
        "Ej: Tengo dolor de muela, ¿puedo agendar una cita?",
        disabled=st.session_state.awaiting_human,
    )

    if user_input:
        process_message(user_input)
        st.rerun()


def main():
    """Función principal de la aplicación."""
    st.set_page_config(
        page_title=f"{BRAND_NAME} - Asistente Dental",
        page_icon="🦷",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

    initialize_app()
    initialize_session()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
