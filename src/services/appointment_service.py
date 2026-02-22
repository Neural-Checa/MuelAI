"""Servicio para gestión de citas y slots disponibles."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import Appointment, Doctor, DoctorSchedule


class AppointmentService:
    """Servicio para citas y disponibilidad de doctores."""

    SLOT_DURATION_MINUTES = 60
    DAYS_AHEAD = 7

    @staticmethod
    def get_available_slots(
        session: Session, doctor_ids: Optional[list[int]] = None
    ) -> list[dict]:
        """
        Genera slots disponibles para los próximos N días.
        Usa DoctorSchedule y excluye citas existentes.
        """
        now = datetime.now()
        today = now.date()
        slots = []

        doctors_query = session.query(Doctor).filter(Doctor.is_available == True)
        if doctor_ids:
            doctors_query = doctors_query.filter(Doctor.id.in_(doctor_ids))
        doctors = doctors_query.all()

        if not doctors:
            return []

        for day_offset in range(AppointmentService.DAYS_AHEAD):
            slot_date = today + timedelta(days=day_offset)
            day_of_week = slot_date.weekday()  # 0=lunes, 6=domingo

            for doctor in doctors:
                schedule = (
                    session.query(DoctorSchedule)
                    .filter(
                        DoctorSchedule.doctor_id == doctor.id,
                        DoctorSchedule.day_of_week == day_of_week,
                    )
                    .first()
                )

                if not schedule:
                    continue

                start_dt = datetime.combine(slot_date, schedule.start_time)
                end_dt = datetime.combine(slot_date, schedule.end_time)

                if day_offset == 0 and now >= start_dt:
                    mins = (
                        (now.minute // AppointmentService.SLOT_DURATION_MINUTES + 1)
                        * AppointmentService.SLOT_DURATION_MINUTES
                    )
                    start_dt = now.replace(minute=0, second=0, microsecond=0)
                    start_dt += timedelta(minutes=mins - now.minute)

                current = start_dt
                slot_end = current + timedelta(
                    minutes=AppointmentService.SLOT_DURATION_MINUTES
                )
                while slot_end <= end_dt:
                    existing = (
                        session.query(Appointment)
                        .filter(
                            Appointment.doctor_id == doctor.id,
                            Appointment.scheduled_at == current,
                            Appointment.status.in_(["scheduled", "confirmed"]),
                        )
                        .first()
                    )
                    if not existing:
                        slot_id = f"{doctor.id}|{current.isoformat()}"
                        slots.append(
                            {
                                "slot_id": slot_id,
                                "doctor_id": doctor.id,
                                "doctor_name": doctor.name,
                                "specialty": doctor.specialty,
                                "scheduled_at": current,
                                "display": current.strftime("%d/%m/%Y %H:%M"),
                            }
                        )
                    current += timedelta(minutes=AppointmentService.SLOT_DURATION_MINUTES)
                    slot_end = current + timedelta(
                        minutes=AppointmentService.SLOT_DURATION_MINUTES
                    )

        return slots

    @staticmethod
    def create_appointment(
        session: Session,
        patient_id: int,
        doctor_id: int,
        scheduled_at: datetime,
        reason: Optional[str] = None,
    ) -> Appointment:
        """Crea una cita."""
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_at=scheduled_at,
            status="scheduled",
            reason=reason,
        )
        session.add(appointment)
        session.flush()
        return appointment

    @staticmethod
    def get_patient_appointments(
        session: Session, patient_id: int, include_past: bool = False
    ) -> list[Appointment]:
        """Obtiene las citas de un paciente."""
        from sqlalchemy.orm import joinedload

        query = (
            session.query(Appointment)
            .options(joinedload(Appointment.doctor))
            .filter(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_at.desc())
        )
        if not include_past:
            query = query.filter(Appointment.scheduled_at >= datetime.now())
        return query.all()
