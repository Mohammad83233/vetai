"""
Clinical input and record models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Symptom(BaseModel):
    """Individual symptom entry."""
    name: str
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    duration_days: Optional[int] = None
    notes: Optional[str] = None


class VitalSigns(BaseModel):
    """Vital signs measurements."""
    temperature_celsius: Optional[float] = Field(None, ge=30, le=50)
    heart_rate_bpm: Optional[int] = Field(None, ge=20, le=400)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=150)
    weight_kg: Optional[float] = Field(None, gt=0)
    body_condition_score: Optional[int] = Field(None, ge=1, le=9)
    hydration_status: Optional[str] = None
    capillary_refill_seconds: Optional[float] = None
    mucous_membrane_color: Optional[str] = None


class ImageInput(BaseModel):
    """Clinical image input."""
    image_id: str
    image_type: str = Field(default="general", description="general, xray, ultrasound, skin, eye, etc.")
    body_part: Optional[str] = None
    notes: Optional[str] = None
    upload_path: Optional[str] = None


class VoiceInput(BaseModel):
    """Voice observation input."""
    audio_id: str
    duration_seconds: float
    transcription: Optional[str] = None
    extracted_symptoms: Optional[List[str]] = None


class ClinicalInput(BaseModel):
    """Multi-modal clinical input for diagnosis."""
    text_description: Optional[str] = Field(None, max_length=5000)
    symptoms: Optional[List[Symptom]] = None
    vital_signs: Optional[VitalSigns] = None
    images: Optional[List[ImageInput]] = None
    voice_notes: Optional[List[VoiceInput]] = None
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None


class ClinicalRecordCreate(BaseModel):
    """Create a new clinical record."""
    patient_id: str
    token_id: Optional[str] = None
    clinical_input: ClinicalInput
    preliminary_notes: Optional[str] = None


class ClinicalRecord(BaseModel):
    """Complete clinical record."""
    id: str = Field(..., alias="_id")
    patient_id: str
    token_id: Optional[str] = None
    doctor_id: str
    clinical_input: ClinicalInput
    extracted_features: Optional[Dict[str, Any]] = None
    diagnosis_id: Optional[str] = None
    treatment_id: Optional[str] = None
    report_id: Optional[str] = None
    status: str = "in_progress"
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
