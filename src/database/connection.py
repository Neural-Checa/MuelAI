from contextlib import contextmanager
from typing import Generator
from datetime import time, date, datetime, timedelta
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base, Doctor, DoctorSchedule, Patient, MedicalHistory, Appointment
from src.settings import get_settings

_engine = None
_SessionLocal = None

# ── Información de la clínica ──────────────────────────────────────────
CLINIC_NAME = "MuelAI PRO"
CLINIC_PHONE = "(01) 456-7890"
CLINIC_WEBSITE = "https://www.clinicasonrisa.pe"
CLINIC_ADDRESS = "Av. Javier Prado Este 1234, San Isidro, Lima"


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


def seed_demo_data() -> None:
    with get_session() as session:
        existing_patient = session.query(Patient).filter_by(dni="76543210").first()
        if existing_patient:
            return

        # ══════════════════════════════════════════════════════════
        #  PACIENTES + HISTORIAL CLÍNICO
        # ══════════════════════════════════════════════════════════

        # ── Paciente 1: María García ──────────────────────────────
        p1 = Patient(
            dni="76543210", name="María García",
            phone="999888777", email="maria.garcia@email.com",
        )
        session.add(p1)
        session.flush()
        session.add_all([
            MedicalHistory(
                patient_id=p1.id,
                date=datetime(2025, 3, 15),
                diagnosis="Caries en molar superior derecho (pieza 16)",
                treatment="Empaste dental con resina compuesta fotocurada",
                notes="Paciente con sensibilidad al frío. Recomendar pasta dental para sensibilidad.",
            ),
            MedicalHistory(
                patient_id=p1.id,
                date=datetime(2025, 9, 20),
                diagnosis="Limpieza dental de rutina",
                treatment="Profilaxis dental completa y aplicación de flúor",
                notes="Buena higiene general. Próxima cita en 6 meses.",
            ),
            MedicalHistory(
                patient_id=p1.id,
                date=datetime(2026, 1, 10),
                diagnosis="Dolor en premolar inferior izquierdo (pieza 34)",
                treatment="Radiografía periapical + medicación analgésica",
                notes="Posible pulpitis reversible. Control en 2 semanas.",
            ),
        ])

        # ── Paciente 2: Carlos López ─────────────────────────────
        p2 = Patient(
            dni="65432109", name="Carlos López",
            phone="999777666", email="carlos.lopez@email.com",
        )
        session.add(p2)
        session.flush()
        session.add_all([
            MedicalHistory(
                patient_id=p2.id,
                date=datetime(2025, 5, 8),
                diagnosis="Gingivitis leve generalizada",
                treatment="Limpieza profunda y recomendaciones de higiene",
                notes="Usar hilo dental diariamente. Control en 3 meses.",
            ),
            MedicalHistory(
                patient_id=p2.id,
                date=datetime(2025, 8, 12),
                diagnosis="Extracción de tercer molar inferior derecho (pieza 48)",
                treatment="Exodoncia quirúrgica bajo anestesia local",
                notes="Sin complicaciones. Receta: Amoxicilina 500mg c/8h x 7 días + Ibuprofeno 400mg c/8h.",
            ),
            MedicalHistory(
                patient_id=p2.id,
                date=datetime(2025, 11, 5),
                diagnosis="Control post-extracción + Limpieza dental",
                treatment="Revisión de alveolo + profilaxis",
                notes="Cicatrización adecuada. Buena evolución.",
            ),
        ])

        # ── Paciente 3: Ana Rodríguez ────────────────────────────
        p3 = Patient(
            dni="54321098", name="Ana Rodríguez",
            phone="999666555", email="ana.rodriguez@email.com",
        )
        session.add(p3)
        session.flush()
        session.add_all([
            MedicalHistory(
                patient_id=p3.id,
                date=datetime(2025, 2, 18),
                diagnosis="Fractura de incisivo central superior (pieza 11)",
                treatment="Corona provisional + planificación de corona definitiva",
                notes="Trauma por caída. Necesita endodoncia previa.",
            ),
            MedicalHistory(
                patient_id=p3.id,
                date=datetime(2025, 3, 5),
                diagnosis="Endodoncia pieza 11",
                treatment="Tratamiento de conducto completo",
                notes="3 conductos tratados. Control radiográfico satisfactorio.",
            ),
            MedicalHistory(
                patient_id=p3.id,
                date=datetime(2025, 4, 20),
                diagnosis="Corona definitiva pieza 11",
                treatment="Cementación de corona de porcelana e-max",
                notes="Muy buen resultado estético. Paciente satisfecha.",
            ),
            MedicalHistory(
                patient_id=p3.id,
                date=datetime(2025, 10, 15),
                diagnosis="Blanqueamiento dental",
                treatment="Blanqueamiento LED en consultorio (2 sesiones)",
                notes="Aclaró 4 tonos. Evitar alimentos pigmentantes por 48h.",
            ),
        ])

        # ── Paciente 4: Jorge Huamán ─────────────────────────────
        p4 = Patient(
            dni="43210987", name="Jorge Huamán",
            phone="999555444", email="jorge.huaman@email.com",
        )
        session.add(p4)
        session.flush()
        session.add_all([
            MedicalHistory(
                patient_id=p4.id,
                date=datetime(2025, 6, 10),
                diagnosis="Periodontitis moderada sectores posteriores",
                treatment="Raspado y alisado radicular cuadrantes 1 y 4",
                notes="Paciente fumador. Indicar cesación tabáquica. Control en 1 mes.",
            ),
            MedicalHistory(
                patient_id=p4.id,
                date=datetime(2025, 7, 15),
                diagnosis="Raspado y alisado radicular cuadrantes 2 y 3",
                treatment="Continuación de tratamiento periodontal",
                notes="Mejoría en profundidad de bolsas. Continuar con clorhexidina.",
            ),
        ])

        # ── Paciente 5: Lucía Fernández ──────────────────────────
        p5 = Patient(
            dni="32109876", name="Lucía Fernández",
            phone="999444333", email="lucia.fernandez@email.com",
        )
        session.add(p5)
        session.flush()
        session.add_all([
            MedicalHistory(
                patient_id=p5.id,
                date=datetime(2025, 4, 22),
                diagnosis="Ortodoncia: maloclusión clase II",
                treatment="Colocación de brackets metálicos arco superior e inferior",
                notes="Duración estimada: 18 meses. Control mensual.",
            ),
            MedicalHistory(
                patient_id=p5.id,
                date=datetime(2025, 12, 10),
                diagnosis="Control ortodóntico mensual #8",
                treatment="Cambio de arco + activación de brackets",
                notes="Buena evolución. Alineación progresando según plan.",
            ),
        ])

        # ══════════════════════════════════════════════════════════
        #  DOCTORES
        # ══════════════════════════════════════════════════════════
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
            is_available=True,
        )
        doctor3 = Doctor(
            name="Dr. Pedro Vargas",
            specialty="Cirugía Oral",
            phone="999555666",
            is_available=True,
        )
        session.add_all([doctor1, doctor2, doctor3])
        session.flush()

        # ══════════════════════════════════════════════════════════
        #  HORARIOS DE DOCTORES
        # ══════════════════════════════════════════════════════════

        # Dr. Roberto Mendoza: Lun-Vie 08:00-13:00 y 14:00-18:00
        for day in range(5):
            session.add(DoctorSchedule(
                doctor_id=doctor1.id, day_of_week=day,
                start_time=time(8, 0), end_time=time(13, 0),
            ))
            session.add(DoctorSchedule(
                doctor_id=doctor1.id, day_of_week=day,
                start_time=time(14, 0), end_time=time(18, 0),
            ))

        # Dra. Ana Castillo: Lun, Mié, Vie 09:00-14:00
        for day in [0, 2, 4]:
            session.add(DoctorSchedule(
                doctor_id=doctor2.id, day_of_week=day,
                start_time=time(9, 0), end_time=time(14, 0),
            ))

        # Dr. Pedro Vargas: Mar, Jue 10:00-17:00, Sáb 09:00-13:00
        for day in [1, 3]:
            session.add(DoctorSchedule(
                doctor_id=doctor3.id, day_of_week=day,
                start_time=time(10, 0), end_time=time(17, 0),
            ))
        session.add(DoctorSchedule(
            doctor_id=doctor3.id, day_of_week=5,
            start_time=time(9, 0), end_time=time(13, 0),
        ))

        # ══════════════════════════════════════════════════════════
        #  CITAS YA OCUPADAS (para demostrar conflictos)
        # ══════════════════════════════════════════════════════════
        today = date.today()

        # Buscar próximos días hábiles de esta semana
        def next_weekday(from_date, weekday):
            """Retorna la próxima fecha con el día de la semana indicado (0=Lun)."""
            days_ahead = weekday - from_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return from_date + timedelta(days=days_ahead)

        # Dr. Mendoza: citas ocupadas Lunes y Miércoles esta/próxima semana
        next_mon = next_weekday(today, 0)
        next_wed = next_weekday(today, 2)

        session.add_all([
            Appointment(
                patient_id=p2.id, doctor_id=doctor1.id,
                appointment_date=next_mon,
                start_time=time(8, 0), end_time=time(8, 30),
                status="scheduled", reason="Control de rutina",
            ),
            Appointment(
                patient_id=p3.id, doctor_id=doctor1.id,
                appointment_date=next_mon,
                start_time=time(9, 0), end_time=time(9, 30),
                status="scheduled", reason="Revisión de corona",
            ),
            Appointment(
                patient_id=p4.id, doctor_id=doctor1.id,
                appointment_date=next_mon,
                start_time=time(10, 0), end_time=time(10, 30),
                status="scheduled", reason="Control periodontal",
            ),
            Appointment(
                patient_id=p1.id, doctor_id=doctor1.id,
                appointment_date=next_wed,
                start_time=time(8, 0), end_time=time(8, 30),
                status="scheduled", reason="Control de empaste",
            ),
            Appointment(
                patient_id=p5.id, doctor_id=doctor1.id,
                appointment_date=next_wed,
                start_time=time(14, 0), end_time=time(14, 30),
                status="scheduled", reason="Limpieza dental",
            ),
        ])

        # Dra. Castillo: citas ocupadas Miércoles y Viernes
        next_fri = next_weekday(today, 4)
        session.add_all([
            Appointment(
                patient_id=p3.id, doctor_id=doctor2.id,
                appointment_date=next_wed,
                start_time=time(9, 0), end_time=time(10, 0),
                status="scheduled", reason="Endodoncia pieza 26",
            ),
            Appointment(
                patient_id=p1.id, doctor_id=doctor2.id,
                appointment_date=next_wed,
                start_time=time(10, 30), end_time=time(11, 30),
                status="scheduled", reason="Evaluación pulpitis",
            ),
            Appointment(
                patient_id=p4.id, doctor_id=doctor2.id,
                appointment_date=next_fri,
                start_time=time(9, 0), end_time=time(9, 30),
                status="scheduled", reason="Control post-endodoncia",
            ),
        ])

        # Dr. Vargas: citas ocupadas Martes y Jueves
        next_tue = next_weekday(today, 1)
        next_thu = next_weekday(today, 3)
        session.add_all([
            Appointment(
                patient_id=p2.id, doctor_id=doctor3.id,
                appointment_date=next_tue,
                start_time=time(10, 0), end_time=time(11, 0),
                status="scheduled", reason="Extracción tercer molar",
            ),
            Appointment(
                patient_id=p5.id, doctor_id=doctor3.id,
                appointment_date=next_thu,
                start_time=time(10, 0), end_time=time(10, 30),
                status="scheduled", reason="Evaluación quirúrgica",
            ),
            Appointment(
                patient_id=p3.id, doctor_id=doctor3.id,
                appointment_date=next_thu,
                start_time=time(14, 0), end_time=time(15, 0),
                status="scheduled", reason="Cirugía de frenillo",
            ),
        ])

        session.commit()
