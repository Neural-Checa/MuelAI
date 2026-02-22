from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=9, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)


class PatientResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MedicalHistoryResponse(BaseModel):
    id: int
    patient_id: int
    date: datetime
    diagnosis: str
    treatment: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str
    phone: str
    is_available: bool

    class Config:
        from_attributes = True


class DoctorAvailability(BaseModel):
    doctor_id: int
    doctor_name: str
    specialty: str
    is_available: bool


class ClassificationResult(BaseModel):
    classification: Literal["general", "urgency", "emergency"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class EmergencyContact(BaseModel):
    name: str
    phone: str
    description: str


class HumanInterventionRequest(BaseModel):
    message: str
    required_action: Literal["update_availability", "assign_doctor", "custom_response"]
    patient_phone: Optional[str] = None
    urgency_level: Optional[str] = None
