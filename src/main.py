import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.database.connection import get_session, init_db, seed_demo_data
from src.graph.graph import create_dental_graph, get_initial_state
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService


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


def render_sidebar():
    """Renderiza el panel lateral con información y controles."""
    st.sidebar.title("Clínica Dental")
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
                        "Toggle",
                        key=f"toggle_{doc.doctor_id}",
                        help="Cambiar disponibilidad",
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
        st.rerun()


def process_message(user_input: str):
    """Procesa un mensaje del usuario a través del grafo."""
    if not st.session_state.patient_phone:
        st.warning("Por favor, ingresa tu número de teléfono en el panel lateral.")
        return

    st.session_state.messages_display.append({"role": "user", "content": user_input})

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
        error_msg = f"Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo."
        st.session_state.messages_display.append(
            {"role": "assistant", "content": error_msg}
        )
        st.error(f"Error: {str(e)}")


def render_chat():
    """Renderiza la interfaz de chat."""
    st.title("Asistente Dental Virtual")
    st.markdown(
        "Bienvenido al chat de consultas de nuestra clínica dental. "
        "Describe tus síntomas o consulta y te ayudaremos."
    )
    st.markdown("---")

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
        page_title="Asistente Dental",
        page_icon="🦷",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_app()
    initialize_session()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
