from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    medical_history: Mapped[list["MedicalHistory"]] = relationship(
        "MedicalHistory", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name={self.name}, phone={self.phone})>"


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    diagnosis: Mapped[str] = mapped_column(String(200), nullable=False)
    treatment: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="medical_history")

    def __repr__(self) -> str:
        return f"<MedicalHistory(id={self.id}, patient_id={self.patient_id}, diagnosis={self.diagnosis})>"


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_chat_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Doctor(id={self.id}, name={self.name}, specialty={self.specialty}, available={self.is_available})>"
