"""Pydantic models for VetAI."""

from .user import User, UserCreate, UserLogin, UserInDB, UserRole, Token, TokenData
from .patient import Patient, PatientCreate, PatientUpdate, Owner, Species
from .queue import QueueToken, QueueTokenCreate, QueueStatus, QueueDisplay
from .clinical import (
    ClinicalInput, 
    ClinicalRecord, 
    ClinicalRecordCreate,
    Symptom,
    VitalSigns,
    ImageInput
)
from .diagnosis import (
    DiagnosisRequest,
    DiagnosisResult,
    DiseasePrediction,
    FollowUpQuestion
)
from .treatment import (
    Treatment,
    TreatmentPlan,
    Medication,
    DosageCalculation,
    Contraindication
)
from .report import SOAPReport, SOAPSection

__all__ = [
    # User
    "User", "UserCreate", "UserLogin", "UserInDB", "UserRole", "Token", "TokenData",
    # Patient
    "Patient", "PatientCreate", "PatientUpdate", "Owner", "Species",
    # Queue
    "QueueToken", "QueueTokenCreate", "QueueStatus", "QueueDisplay",
    # Clinical
    "ClinicalInput", "ClinicalRecord", "ClinicalRecordCreate", 
    "Symptom", "VitalSigns", "ImageInput",
    # Diagnosis
    "DiagnosisRequest", "DiagnosisResult", "DiseasePrediction", "FollowUpQuestion",
    # Treatment
    "Treatment", "TreatmentPlan", "Medication", "DosageCalculation", "Contraindication",
    # Report
    "SOAPReport", "SOAPSection"
]
