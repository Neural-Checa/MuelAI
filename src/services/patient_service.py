from typing import Optional

from sqlalchemy.orm import Session, joinedload

from src.database.models import MedicalHistory, Patient


class PatientService:
    @staticmethod
    def get_patient_by_phone(session: Session, phone: str) -> Optional[Patient]:
        return session.query(Patient).filter(Patient.phone == phone).first()

    @staticmethod
    def get_patient_by_email(session: Session, email: str) -> Optional[Patient]:
        return session.query(Patient).filter(Patient.email == email).first()

    @staticmethod
    def get_patient_with_history(
        session: Session, patient_id: int
    ) -> Optional[Patient]:
        return (
            session.query(Patient)
            .options(joinedload(Patient.medical_history))
            .filter(Patient.id == patient_id)
            .first()
        )

    @staticmethod
    def create_patient(
        session: Session, name: str, phone: str, email: Optional[str] = None
    ) -> Patient:
        patient = Patient(name=name, phone=phone, email=email)
        session.add(patient)
        session.flush()
        return patient

    @staticmethod
    def get_medical_history_summary(session: Session, patient_id: int) -> str:
        history_records = (
            session.query(MedicalHistory)
            .filter(MedicalHistory.patient_id == patient_id)
            .order_by(MedicalHistory.date.desc())
            .all()
        )

        if not history_records:
            return "El paciente no tiene historial médico registrado."

        summary_parts = ["Historial médico del paciente:"]
        for record in history_records:
            date_str = record.date.strftime("%d/%m/%Y")
            summary_parts.append(
                f"\n- Fecha: {date_str}\n"
                f"  Diagnóstico: {record.diagnosis}\n"
                f"  Tratamiento: {record.treatment}"
            )
            if record.notes:
                summary_parts.append(f"\n  Notas: {record.notes}")

        return "".join(summary_parts)

    @staticmethod
    def patient_exists(session: Session, phone: str) -> bool:
        return (
            session.query(Patient).filter(Patient.phone == phone).first() is not None
        )
