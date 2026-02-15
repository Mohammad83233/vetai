"""
Diagnosis and disease prediction models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DiseasePrediction(BaseModel):
    """Individual disease prediction."""
    disease_name: str
    disease_code: Optional[str] = None
    probability: float = Field(..., ge=0, le=1)
    confidence: str = Field(default="medium", pattern="^(low|medium|high)$")
    species_specific: bool = True
    common_symptoms: Optional[List[str]] = None
    matched_symptoms: Optional[List[str]] = None
    verification_symptoms: Optional[List[str]] = None
    all_disease_symptoms: Optional[List[str]] = None
    new_matched_symptoms: Optional[List[str]] = None
    description: Optional[str] = None
    urgency: str = Field(default="routine", pattern="^(routine|soon|urgent|emergency)$")
    refined_score: Optional[float] = None
    total_matched: Optional[int] = None
    normalized_confidence: Optional[float] = None
    symptom_confidence: Optional[int] = None  # (matched/8)*100, the ONLY confidence shown in UI


class FollowUpQuestion(BaseModel):
    """Follow-up question for diagnosis refinement."""
    question_id: str
    question_text: str
    question_type: str = "text"  # text, yes_no, multiple_choice, numeric
    options: Optional[List[str]] = None
    importance: str = "medium"
    related_diseases: Optional[List[str]] = None


class DiagnosisRequest(BaseModel):
    """Request for AI diagnosis."""
    patient_id: str
    clinical_record_id: Optional[str] = None
    species: str
    breed: Optional[str] = None
    weight_kg: float
    age_months: int
    symptoms: List[str]
    temperature: Optional[float] = None
    heart_rate: Optional[float] = None
    duration_days: Optional[int] = None
    symptom_details: Optional[Dict[str, Any]] = None
    vital_signs: Optional[Dict[str, Any]] = None
    image_features: Optional[Dict[str, Any]] = None
    voice_features: Optional[Dict[str, Any]] = None
    verified_symptoms: Optional[List[str]] = None  # Symptoms confirmed by doctor
    previous_diagnosis_id: Optional[str] = None  # For iterative refinement


class DiagnosisResult(BaseModel):
    """AI diagnosis result."""
    id: str = Field(..., alias="_id")
    patient_id: str
    clinical_record_id: Optional[str] = None
    predictions: List[DiseasePrediction]
    top_prediction: Optional[DiseasePrediction] = None
    follow_up_questions: Optional[List[FollowUpQuestion]] = None
    followup_symptoms: Optional[List[str]] = None
    confidence_score: float = Field(..., ge=0, le=1)
    requires_more_info: bool = False
    ai_notes: Optional[str] = None
    model_version: str = "1.0.0"
    created_at: datetime
    final_diagnosis: Optional[str] = None
    previous_diagnosis_id: Optional[str] = None
    
    class Config:
        populate_by_name = True


class DiagnosisAnswer(BaseModel):
    """Answer to a follow-up question for refinement."""
    question_id: str
    answer: str
    answer_details: Optional[Dict[str, Any]] = None


class DiagnosisRefineRequest(BaseModel):
    """Request to refine diagnosis with additional info (legacy)."""
    diagnosis_id: str
    answers: List[DiagnosisAnswer]
    additional_symptoms: Optional[List[str]] = None


class RefineWithSymptomsRequest(BaseModel):
    """Request to refine prediction with doctor-selected follow-up symptoms."""
    diagnosis_id: str
    selected_symptoms: List[str]


class FinalDiagnosisRequest(BaseModel):
    """Request to set the doctor's final diagnosis choice."""
    diagnosis_id: str
    selected_disease: str
