from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Doctor
from src.services.doctor_service import DoctorService
from src.services.patient_service import PatientService


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_patient_service_create_and_find() -> None:
    session = _make_session()
    try:
        created = PatientService.create_patient(
            session,
            name="Paciente Test",
            phone="+51999999999",
            email="test@example.com",
        )
        session.commit()

        found = PatientService.get_patient_by_phone(session, "+51999999999")

        assert found is not None
        assert created.id == found.id
        assert found.name == "Paciente Test"
    finally:
        session.close()


def test_doctor_service_availability_toggle() -> None:
    session = _make_session()
    try:
        doctor = Doctor(
            name="Dr. Toggle",
            specialty="Odontologia General",
            phone="+51888888888",
            is_available=False,
        )
        session.add(doctor)
        session.commit()

        updated = DoctorService.set_doctor_availability(session, doctor.id, True)
        session.commit()

        assert updated is not None
        refreshed = DoctorService.get_doctor_by_id(session, doctor.id)
        assert refreshed is not None
        assert refreshed.is_available is True
    finally:
        session.close()


def test_doctor_service_assign_and_release() -> None:
    session = _make_session()
    try:
        doctor = Doctor(
            name="Dr. Assign",
            specialty="Urgencias",
            phone="+51777777777",
            is_available=True,
        )
        session.add(doctor)
        session.commit()

        assigned = DoctorService.assign_doctor_to_chat(session, doctor.id, "chat-123")
        session.commit()

        assert assigned is not None
        assert assigned.current_chat_id == "chat-123"
        assert assigned.is_available is False

        released = DoctorService.release_doctor(session, doctor.id)
        session.commit()

        assert released is not None
        assert released.current_chat_id is None
        assert released.is_available is True
    finally:
        session.close()
