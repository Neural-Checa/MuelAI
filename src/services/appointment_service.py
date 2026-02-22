from datetime import date, time, datetime, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.database.models import Appointment, DoctorSchedule


class AppointmentService:
    """Servicio para gestionar citas y verificar conflictos de horarios."""

    @staticmethod
    def get_doctor_schedule(session: Session, doctor_id: int) -> list[DoctorSchedule]:
        return (
            session.query(DoctorSchedule)
            .filter(DoctorSchedule.doctor_id == doctor_id)
            .order_by(DoctorSchedule.day_of_week, DoctorSchedule.start_time)
            .all()
        )

    @staticmethod
    def check_conflict(
        session: Session,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
    ) -> bool:
        """Retorna True si existe un cruce de horario para el doctor en esa fecha/hora."""
        conflicting = (
            session.query(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date == appointment_date,
                    Appointment.status == "scheduled",
                    Appointment.start_time < end_time,
                    Appointment.end_time > start_time,
                )
            )
            .first()
        )
        return conflicting is not None

    @staticmethod
    def is_within_schedule(
        session: Session,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
    ) -> bool:
        """Verifica si el horario solicitado cae dentro del horario del doctor."""
        day_of_week = appointment_date.weekday()  # 0=Lun, 6=Dom
        schedules = (
            session.query(DoctorSchedule)
            .filter(
                and_(
                    DoctorSchedule.doctor_id == doctor_id,
                    DoctorSchedule.day_of_week == day_of_week,
                )
            )
            .all()
        )
        for sched in schedules:
            if sched.start_time <= start_time and sched.end_time >= end_time:
                return True
        return False

    @staticmethod
    def create_appointment(
        session: Session,
        patient_id: int,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        reason: Optional[str] = None,
    ) -> tuple[Optional[Appointment], str]:
        """
        Crea una cita si no hay conflictos.
        Retorna (Appointment, "") o (None, "mensaje de error").
        """
        # Verificar que está dentro del horario del doctor
        if not AppointmentService.is_within_schedule(
            session, doctor_id, appointment_date, start_time, end_time
        ):
            return None, "El horario solicitado está fuera del horario de atención del doctor."

        # Verificar conflictos
        if AppointmentService.check_conflict(
            session, doctor_id, appointment_date, start_time, end_time
        ):
            return None, "Ya existe una cita programada en ese horario. Por favor, elija otro horario."

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )
        session.add(appointment)
        session.flush()
        return appointment, ""

    @staticmethod
    def get_patient_appointments(
        session: Session, patient_id: int
    ) -> list[Appointment]:
        return (
            session.query(Appointment)
            .filter(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == "scheduled",
                )
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
            .all()
        )

    @staticmethod
    def get_next_available_slot(
        session: Session,
        doctor_id: int,
        from_date: date,
        duration_minutes: int = 30,
    ) -> Optional[tuple[date, time, time]]:
        """Busca el siguiente slot disponible para un doctor a partir de una fecha."""
        for day_offset in range(14):  # Buscar hasta 2 semanas
            check_date = from_date + timedelta(days=day_offset)
            day_of_week = check_date.weekday()

            schedules = (
                session.query(DoctorSchedule)
                .filter(
                    and_(
                        DoctorSchedule.doctor_id == doctor_id,
                        DoctorSchedule.day_of_week == day_of_week,
                    )
                )
                .order_by(DoctorSchedule.start_time)
                .all()
            )

            for sched in schedules:
                current_time = sched.start_time
                end_limit = sched.end_time

                while True:
                    slot_end_dt = (
                        datetime.combine(check_date, current_time)
                        + timedelta(minutes=duration_minutes)
                    )
                    slot_end = slot_end_dt.time()

                    if slot_end > end_limit:
                        break

                    if not AppointmentService.check_conflict(
                        session, doctor_id, check_date, current_time, slot_end
                    ):
                        return (check_date, current_time, slot_end)

                    current_time = slot_end

        return None
