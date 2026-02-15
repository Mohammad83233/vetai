"""
Treatment and dosage models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DosageCalculation(BaseModel):
    """Calculated medication dosage."""
    medication_name: str
    dose_mg: float
    dose_per_kg: float
    frequency: str  # e.g., "twice daily", "every 8 hours"
    duration_days: int
    route: str  # oral, injection, topical, etc.
    total_amount: float
    unit: str  # mg, ml, tablets, etc.
    instructions: str
    species_adjustment: float = 1.0
    weight_factor: float = 1.0
    condition_factor: float = 1.0


class Contraindication(BaseModel):
    """Drug contraindication or interaction alert."""
    alert_type: str = Field(..., pattern="^(contraindication|interaction|warning|caution)$")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    medication: str
    reason: str
    conflicting_medication: Optional[str] = None
    conflicting_condition: Optional[str] = None
    recommendation: str


class Medication(BaseModel):
    """Individual medication in treatment plan."""
    name: str
    generic_name: Optional[str] = None
    category: str  # antibiotic, analgesic, anti-inflammatory, etc.
    dosage: DosageCalculation
    purpose: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class Treatment(BaseModel):
    """Individual treatment procedure."""
    name: str
    type: str  # medication, procedure, surgery, therapy, diet, etc.
    description: str
    priority: int = Field(default=0, ge=0, le=10)
    estimated_cost: Optional[float] = None
    duration: Optional[str] = None


class TreatmentPlan(BaseModel):
    """Complete treatment plan."""
    id: str = Field(..., alias="_id")
    patient_id: str
    diagnosis_id: str
    clinical_record_id: Optional[str] = None
    primary_diagnosis: str
    medications: List[Medication] = []
    treatments: List[Treatment] = []
    contraindications: List[Contraindication] = []
    dietary_recommendations: Optional[str] = None
    activity_restrictions: Optional[str] = None
    follow_up_schedule: Optional[List[str]] = None
    monitoring_instructions: Optional[str] = None
    prognosis: Optional[str] = None
    emergency_instructions: Optional[str] = None
    total_estimated_cost: Optional[float] = None
    created_at: datetime
    created_by: str
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class TreatmentRequest(BaseModel):
    """Request for treatment recommendation."""
    patient_id: str
    diagnosis_id: str
    species: str
    weight_kg: float
    age_months: int
    diseases: List[str]
    current_medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    conditions: Optional[List[str]] = None


class DosageRequest(BaseModel):
    """Request for dosage calculation."""
    medication_name: str
    species: str
    weight_kg: float
    age_months: int
    condition: Optional[str] = None
    route: str = "oral"
