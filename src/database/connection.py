from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import (
    Base,
    Appointment,
    Doctor,
    DoctorSchedule,
    MedicalHistory,
    Patient,
)
from src.settings import get_settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def _seed_doctor_schedules(session, doctors) -> None:
    """Agrega horarios L-V 9-17 para doctores que no tengan."""
    from datetime import time

    for doc in doctors:
        existing = (
            session.query(DoctorSchedule)
            .filter(DoctorSchedule.doctor_id == doc.id)
            .first()
        )
        if not existing:
            for day in range(5):
                schedule = DoctorSchedule(
                    doctor_id=doc.id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
                session.add(schedule)


def seed_demo_data() -> None:
    # Siempre asegurar que doctores existentes tengan horarios
    with get_session() as session:
        doctors = session.query(Doctor).all()
        _seed_doctor_schedules(session, doctors)

    with get_session() as session:
        existing_patient = session.query(Patient).filter_by(phone="999888777").first()
        if existing_patient:
            return

        patient1 = Patient(
            name="María García",
            phone="999888777",
            email="maria.garcia@email.com",
        )
        session.add(patient1)
        session.flush()

        history1 = MedicalHistory(
            patient_id=patient1.id,
            diagnosis="Caries en molar superior derecho",
            treatment="Empaste dental con resina compuesta",
            notes="Paciente con sensibilidad al frío. Recomendar pasta dental para sensibilidad.",
        )
        history2 = MedicalHistory(
            patient_id=patient1.id,
            diagnosis="Limpieza dental de rutina",
            treatment="Profilaxis dental completa",
            notes="Buena higiene general. Próxima cita en 6 meses.",
        )
        session.add_all([history1, history2])

        patient2 = Patient(
            name="Carlos López",
            phone="999777666",
            email="carlos.lopez@email.com",
        )
        session.add(patient2)
        session.flush()

        history3 = MedicalHistory(
            patient_id=patient2.id,
            diagnosis="Gingivitis leve",
            treatment="Limpieza profunda y recomendaciones de higiene",
            notes="Usar hilo dental diariamente. Control en 3 meses.",
        )
        session.add(history3)

        doctor1 = Doctor(
            name="Dr. Roberto Mendoza",
            specialty="Odontología General",
            phone="999111222",
            is_available=True,
        )
        doctor2 = Doctor(
            name="Dra. Ana Castillo",
            specialty="Endodoncia",
            phone="999333444",
            is_available=False,
        )
        doctor3 = Doctor(
            name="Dr. Pedro Vargas",
            specialty="Cirugía Oral",
            phone="999555666",
            is_available=True,
        )
        session.add_all([doctor1, doctor2, doctor3])
        session.flush()

        _seed_doctor_schedules(session, [doctor1, doctor2, doctor3])
        session.commit()
