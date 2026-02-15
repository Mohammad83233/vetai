"""
Treatment and dosage API routes.
"""

from fastapi import APIRouter, HTTPException, status, Depends

from ..models.treatment import (
    TreatmentPlan,
    TreatmentRequest,
    DosageRequest,
    DosageCalculation
)
from ..models.user import User
from ..services.clinical_service import ClinicalService
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/treatment", tags=["Treatment & Dosage"])


# Demo medication database
MEDICATION_DATABASE = {
    "amoxicillin": {
        "name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "category": "antibiotic",
        "base_dose_mg_per_kg": 10,
        "frequency": "twice daily",
        "duration_days": 7,
        "route": "oral",
        "species_factors": {"dog": 1.0, "cat": 0.8, "rabbit": 0.5},
        "contraindications": ["penicillin allergy", "kidney disease"],
        "interactions": ["methotrexate", "warfarin"]
    },
    "metronidazole": {
        "name": "Metronidazole",
        "generic_name": "Metronidazole",
        "category": "antibiotic",
        "base_dose_mg_per_kg": 15,
        "frequency": "twice daily",
        "duration_days": 7,
        "route": "oral",
        "species_factors": {"dog": 1.0, "cat": 0.8},
        "contraindications": ["pregnancy", "liver disease"],
        "interactions": ["alcohol", "lithium"]
    },
    "meloxicam": {
        "name": "Meloxicam",
        "generic_name": "Meloxicam",
        "category": "nsaid",
        "base_dose_mg_per_kg": 0.1,
        "frequency": "once daily",
        "duration_days": 5,
        "route": "oral",
        "species_factors": {"dog": 1.0, "cat": 0.5},
        "contraindications": ["kidney disease", "gi ulcers", "dehydration"],
        "interactions": ["other nsaids", "corticosteroids"]
    },
    "gabapentin": {
        "name": "Gabapentin",
        "generic_name": "Gabapentin",
        "category": "analgesic",
        "base_dose_mg_per_kg": 5,
        "frequency": "twice daily",
        "duration_days": 14,
        "route": "oral",
        "species_factors": {"dog": 1.0, "cat": 1.2},
        "contraindications": ["severe kidney disease"],
        "interactions": ["antacids"]
    },
    "cerenia": {
        "name": "Cerenia",
        "generic_name": "Maropitant",
        "category": "antiemetic",
        "base_dose_mg_per_kg": 2,
        "frequency": "once daily",
        "duration_days": 5,
        "route": "oral",
        "species_factors": {"dog": 1.0, "cat": 1.0},
        "contraindications": ["gi obstruction"],
        "interactions": []
    }
}


def calculate_dosage(
    medication_name: str,
    species: str,
    weight_kg: float,
    age_months: int,
    condition: str = None
) -> DosageCalculation:
    """Calculate medication dosage."""
    med_key = medication_name.lower()
    med = MEDICATION_DATABASE.get(med_key)
    
    if not med:
        # Default calculation for unknown medications
        return DosageCalculation(
            medication_name=medication_name,
            dose_mg=weight_kg * 10,  # Default 10mg/kg
            dose_per_kg=10,
            frequency="twice daily",
            duration_days=7,
            route="oral",
            total_amount=weight_kg * 10 * 14,  # 7 days * 2 doses
            unit="mg",
            instructions=f"Give {weight_kg * 10:.1f}mg twice daily for 7 days",
            species_adjustment=1.0,
            weight_factor=1.0,
            condition_factor=1.0
        )
    
    # Get species factor
    species_factor = med["species_factors"].get(species.lower(), 1.0)
    
    # Age adjustments
    age_factor = 1.0
    if age_months < 6:
        age_factor = 0.75  # Young animals
    elif age_months > 120:
        age_factor = 0.85  # Senior animals
    
    # Condition adjustments
    condition_factor = 1.0
    if condition:
        if "severe" in condition.lower():
            condition_factor = 1.2
        elif "mild" in condition.lower():
            condition_factor = 0.8
    
    # Calculate dose
    base_dose = med["base_dose_mg_per_kg"]
    adjusted_dose_per_kg = base_dose * species_factor * age_factor * condition_factor
    total_dose = adjusted_dose_per_kg * weight_kg
    
    # Calculate total amount for duration
    doses_per_day = 2 if "twice" in med["frequency"] else 1
    total_doses = doses_per_day * med["duration_days"]
    total_amount = total_dose * total_doses
    
    return DosageCalculation(
        medication_name=med["name"],
        dose_mg=round(total_dose, 2),
        dose_per_kg=round(adjusted_dose_per_kg, 2),
        frequency=med["frequency"],
        duration_days=med["duration_days"],
        route=med["route"],
        total_amount=round(total_amount, 2),
        unit="mg",
        instructions=f"Give {total_dose:.1f}mg {med['frequency']} for {med['duration_days']} days via {med['route']} route",
        species_adjustment=species_factor,
        weight_factor=age_factor,
        condition_factor=condition_factor
    )


@router.post("/recommend")
async def recommend_treatment(
    request: TreatmentRequest,
    current_user: User = Depends(require_doctor)
):
    """Get treatment recommendations for diagnosed conditions."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database
    
    # Demo treatment recommendations based on disease
    disease_treatments = {
        "canine parvovirus": ["metronidazole", "cerenia"],
        "kennel cough": ["amoxicillin"],
        "gastritis": ["cerenia", "metronidazole"],
        "feline upper respiratory infection": ["amoxicillin"],
        "urinary tract infection": ["amoxicillin"],
        "gi stasis": ["metronidazole"],
    }
    
    medications = []
    contraindications = []
    
    for disease in request.diseases:
        disease_key = disease.lower().strip()
        meds = disease_treatments.get(disease_key, ["amoxicillin"])
        
        for med_name in meds:
            # Calculate dosage
            dosage = calculate_dosage(
                med_name,
                request.species,
                request.weight_kg,
                request.age_months
            )
            
            med_info = MEDICATION_DATABASE.get(med_name.lower(), {})
            
            medications.append({
                "name": dosage.medication_name,
                "generic_name": med_info.get("generic_name", med_name),
                "category": med_info.get("category", "general"),
                "dosage": dosage.model_dump(),
                "purpose": f"Treatment for {disease}"
            })
            
            # Check contraindications
            if request.allergies:
                for allergy in request.allergies:
                    for contra in med_info.get("contraindications", []):
                        if allergy.lower() in contra.lower():
                            contraindications.append({
                                "alert_type": "contraindication",
                                "severity": "high",
                                "medication": dosage.medication_name,
                                "reason": f"Patient allergy: {allergy}",
                                "conflicting_condition": allergy,
                                "recommendation": f"Consider alternative to {dosage.medication_name}"
                            })
            
            # Check drug interactions
            if request.current_medications:
                for current_med in request.current_medications:
                    for interaction in med_info.get("interactions", []):
                        if interaction.lower() in current_med.lower():
                            contraindications.append({
                                "alert_type": "interaction",
                                "severity": "medium",
                                "medication": dosage.medication_name,
                                "reason": f"Drug interaction with {current_med}",
                                "conflicting_medication": current_med,
                                "recommendation": f"Monitor closely or adjust timing"
                            })
    
    # Create treatment plan
    treatments = Database.get_collection("treatments")
    
    treatment_doc = {
        "patient_id": request.patient_id,
        "diagnosis_id": request.diagnosis_id,
        "primary_diagnosis": request.diseases[0] if request.diseases else "Unknown",
        "medications": medications,
        "treatments": [
            {"name": "Follow-up examination", "type": "procedure", "description": "Re-examine in 7-10 days", "priority": 1},
            {"name": "Monitor symptoms", "type": "monitoring", "description": "Watch for improvement or worsening", "priority": 2}
        ],
        "contraindications": contraindications,
        "dietary_recommendations": "Bland diet recommended for GI conditions. Ensure adequate hydration.",
        "activity_restrictions": "Limit activity if showing lethargy. Rest is important for recovery.",
        "follow_up_schedule": ["7 days - Progress check", "14 days - Final evaluation if needed"],
        "monitoring_instructions": "Monitor appetite, energy levels, and symptom progression daily.",
        "emergency_instructions": "Seek immediate care if symptoms worsen, breathing difficulty, or collapse occurs.",
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "approved": False
    }
    
    result = await treatments.insert_one(treatment_doc)
    treatment_doc["_id"] = str(result.inserted_id)
    
    return TreatmentPlan(**treatment_doc)


@router.post("/dosage", response_model=DosageCalculation)
async def calculate_medication_dosage(
    request: DosageRequest,
    current_user: User = Depends(require_doctor)
):
    """Calculate dosage for a specific medication."""
    return calculate_dosage(
        request.medication_name,
        request.species,
        request.weight_kg,
        request.age_months,
        request.condition
    )


@router.get("/{treatment_id}")
async def get_treatment(
    treatment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get treatment plan by ID."""
    from bson import ObjectId
    from ..database import Database
    
    treatments = Database.get_collection("treatments")
    
    try:
        treatment = await treatments.find_one({"_id": ObjectId(treatment_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    treatment["_id"] = str(treatment["_id"])
    return TreatmentPlan(**treatment)


@router.post("/{treatment_id}/approve")
async def approve_treatment(
    treatment_id: str,
    current_user: User = Depends(require_doctor)
):
    """Approve a treatment plan."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database
    
    treatments = Database.get_collection("treatments")
    
    result = await treatments.find_one_and_update(
        {"_id": ObjectId(treatment_id)},
        {
            "$set": {
                "approved": True,
                "approved_by": current_user.id,
                "approved_at": datetime.utcnow()
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    result["_id"] = str(result["_id"])
    return TreatmentPlan(**result)
