import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src.database.connection import get_session, init_db, seed_demo_data
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService


def _initialize() -> None:
    init_db()
    seed_demo_data()


def _render_doctors() -> None:
    st.subheader("Doctores")
    with get_session() as session:
        doctors = DoctorService.get_all_doctors(session)
        for doc in doctors:
            col1, col2 = st.columns([4, 1])
            with col1:
                status = "Disponible" if doc.is_available else "No disponible"
                st.write(f"{doc.doctor_name} - {doc.specialty} ({status})")
            with col2:
                if st.button("Toggle", key=f"doctor_{doc.doctor_id}"):
                    DoctorService.set_doctor_availability(
                        session,
                        doc.doctor_id,
                        not doc.is_available,
                    )
                    session.commit()
                    st.rerun()


def _render_patients() -> None:
    st.subheader("Pacientes")
    with get_session() as session:
        # There is no list API on PatientService; reuse known demo phones for quick panel.
        demo_phones = ["999888777", "999777666"]
        for phone in demo_phones:
            patient = PatientService.get_patient_by_phone(session, phone)
            if patient:
                st.write(f"{patient.name} - {patient.phone}")


def main() -> None:
    st.set_page_config(page_title="MuelAI Admin", page_icon="🦷", layout="wide")
    st.title("MuelAI Admin")
    _initialize()

    tab_doctors, tab_patients = st.tabs(["Doctores", "Pacientes"])
    with tab_doctors:
        _render_doctors()
    with tab_patients:
        _render_patients()


if __name__ == "__main__":
    main()
