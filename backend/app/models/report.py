"""
SOAP report models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SOAPSection(BaseModel):
    """Generic SOAP section content."""
    content: str
    details: Optional[Dict[str, Any]] = None


class SubjectiveSection(BaseModel):
    """S - Subjective observations from owner."""
    chief_complaint: str
    history_of_present_illness: Optional[str] = None
    owner_observations: Optional[List[str]] = None
    duration: Optional[str] = None
    onset: Optional[str] = None
    changes_noticed: Optional[str] = None
    appetite: Optional[str] = None
    water_intake: Optional[str] = None
    urination: Optional[str] = None
    defecation: Optional[str] = None
    activity_level: Optional[str] = None
    raw_text: Optional[str] = None


class ObjectiveSection(BaseModel):
    """O - Objective clinical findings."""
    vital_signs: Optional[Dict[str, Any]] = None
    physical_exam_findings: Optional[List[str]] = None
    weight_kg: Optional[float] = None
    body_condition_score: Optional[int] = None
    lab_results: Optional[Dict[str, Any]] = None
    imaging_findings: Optional[List[str]] = None
    image_references: Optional[List[str]] = None
    other_tests: Optional[Dict[str, Any]] = None


class AssessmentSection(BaseModel):
    """A - Assessment/diagnosis."""
    primary_diagnosis: str
    differential_diagnoses: Optional[List[str]] = None
    ai_predictions: Optional[List[Dict[str, Any]]] = None
    ai_confidence: Optional[float] = None
    veterinarian_notes: Optional[str] = None
    prognosis: Optional[str] = None
    disease_stage: Optional[str] = None


class PlanSection(BaseModel):
    """P - Plan for treatment and follow-up."""
    medications: Optional[List[Dict[str, Any]]] = None
    procedures: Optional[List[str]] = None
    dietary_recommendations: Optional[str] = None
    activity_restrictions: Optional[str] = None
    home_care_instructions: Optional[str] = None
    follow_up_appointments: Optional[List[str]] = None
    monitoring_instructions: Optional[str] = None
    emergency_instructions: Optional[str] = None
    referrals: Optional[List[str]] = None
    estimated_cost: Optional[float] = None


class SOAPReport(BaseModel):
    """Complete SOAP clinical report."""
    id: str = Field(..., alias="_id")
    patient_id: str
    clinical_record_id: str
    diagnosis_id: Optional[str] = None
    treatment_id: Optional[str] = None
    token_id: Optional[str] = None
    
    # Patient info snapshot
    patient_name: str
    species: str
    breed: Optional[str] = None
    weight_kg: float
    age_months: int
    owner_name: str
    
    # SOAP sections
    subjective: SubjectiveSection
    objective: ObjectiveSection
    assessment: AssessmentSection
    plan: PlanSection
    
    # Metadata
    created_at: datetime
    created_by: str  # Doctor ID
    doctor_name: str
    clinic_name: str = "VetAI Clinic"
    
    # Status
    status: str = Field(default="draft", pattern="^(draft|final|amended)$")
    finalized_at: Optional[datetime] = None
    amendments: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        populate_by_name = True


class SOAPReportCreate(BaseModel):
    """Create SOAP report request."""
    patient_id: str
    clinical_record_id: str
    diagnosis_id: Optional[str] = None
    treatment_id: Optional[str] = None
    auto_generate: bool = True  # Auto-fill from clinical data


class SOAPReportExport(BaseModel):
    """Export options for SOAP report."""
    report_id: str
    format: str = Field(default="pdf", pattern="^(pdf|json|html)$")
    include_images: bool = True
    include_ai_details: bool = False
