from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import Doctor
from src.schemas.models import DoctorAvailability


class DoctorService:
    @staticmethod
    def get_available_doctors(session: Session) -> list[DoctorAvailability]:
        doctors = (
            session.query(Doctor).filter(Doctor.is_available == True).all()
        )
        return [
            DoctorAvailability(
                doctor_id=doc.id,
                doctor_name=doc.name,
                specialty=doc.specialty,
                is_available=doc.is_available,
            )
            for doc in doctors
        ]

    @staticmethod
    def get_all_doctors(session: Session) -> list[DoctorAvailability]:
        doctors = session.query(Doctor).all()
        return [
            DoctorAvailability(
                doctor_id=doc.id,
                doctor_name=doc.name,
                specialty=doc.specialty,
                is_available=doc.is_available,
            )
            for doc in doctors
        ]

    @staticmethod
    def set_doctor_availability(
        session: Session, doctor_id: int, is_available: bool
    ) -> Optional[Doctor]:
        doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            doctor.is_available = is_available
            session.flush()
        return doctor

    @staticmethod
    def assign_doctor_to_chat(
        session: Session, doctor_id: int, chat_id: str
    ) -> Optional[Doctor]:
        doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            doctor.current_chat_id = chat_id
            doctor.is_available = False
            session.flush()
        return doctor

    @staticmethod
    def release_doctor(session: Session, doctor_id: int) -> Optional[Doctor]:
        doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            doctor.current_chat_id = None
            doctor.is_available = True
            session.flush()
        return doctor

    @staticmethod
    def get_doctor_by_id(session: Session, doctor_id: int) -> Optional[Doctor]:
        return session.query(Doctor).filter(Doctor.id == doctor_id).first()
