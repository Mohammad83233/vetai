"""
AI Diagnosis API routes.
Uses trained XGBoost model for disease prediction with follow-up
symptom refinement and doctor-controlled final diagnosis.
"""

from fastapi import APIRouter, HTTPException, status, Depends

from ..models.diagnosis import (
    DiagnosisRequest,
    DiagnosisResult,
    DiagnosisRefineRequest,
    RefineWithSymptomsRequest,
    FinalDiagnosisRequest
)
from ..models.user import User
from ..services.clinical_service import ClinicalService
from ..services.prediction_service import (
    predict_diseases,
    get_followup_symptoms,
    refine_predictions
)
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/diagnosis", tags=["AI Diagnosis"])


@router.get("/ping")
async def ping_diagnosis():
    """Simple ping to test connectivity and CORS for this router."""
    return {"status": "ok", "message": "Diagnosis router is reachable"}


async def get_ai_prediction(request: DiagnosisRequest) -> dict:
    """Get disease prediction from the trained XGBoost model."""
    from datetime import datetime

    # Combine original symptoms with any verified symptoms from doctor
    all_symptoms = list(request.symptoms)
    if request.verified_symptoms:
        all_symptoms.extend(request.verified_symptoms)
    # Deduplicate
    all_symptoms = list(dict.fromkeys(all_symptoms))

    # Call trained model
    predictions = predict_diseases(
        species=request.species,
        breed=request.breed,
        symptoms=all_symptoms,
        weight_kg=request.weight_kg,
        age_months=request.age_months,
        temperature=request.temperature,
        heart_rate=request.heart_rate,
        duration_days=request.duration_days,
        top_n=3
    )

    # Build combined follow-up symptom list from Top 3 predictions
    followup_symptoms = get_followup_symptoms(predictions)

    top = predictions[0] if predictions else None

    ai_notes = f"Prediction from trained XGBoost model ({len(all_symptoms)} symptoms analyzed)."
    if request.verified_symptoms:
        ai_notes += f" Refined with {len(request.verified_symptoms)} doctor-verified symptoms."

    return {
        "predictions": predictions[:3],
        "top_prediction": top,
        "follow_up_questions": [],  # Deprecated — using followup_symptoms instead
        "followup_symptoms": followup_symptoms,
        "confidence_score": min(1.0, max(0.0, (top["symptom_confidence"] / 100.0))) if top else 0.0,
        "requires_more_info": len(followup_symptoms) > 0,
        "ai_notes": ai_notes,
        "model_version": "xgboost-1.0.0",
        "created_at": datetime.utcnow()
    }


@router.post("/predict", response_model=DiagnosisResult, response_model_by_alias=False)
async def predict_diagnosis(
    request: DiagnosisRequest,
    current_user: User = Depends(require_doctor)
):
    """Get AI-powered disease predictions based on symptoms using trained model."""
    from bson import ObjectId
    from ..database import Database
    import traceback
    
    print(f"🎯 TRACE: predict_diagnosis called for patient {request.patient_id}")

    try:
        # Get prediction from trained AI model
        prediction = await get_ai_prediction(request)

        # Save diagnosis to database
        diagnoses = Database.get_collection("diagnoses")

        diagnosis_doc = {
            "patient_id": request.patient_id,
            "clinical_record_id": request.clinical_record_id,
            **prediction
        }

        result = await diagnoses.insert_one(diagnosis_doc)
        diagnosis_doc["_id"] = str(result.inserted_id)

        # Link to clinical record if provided (validate it's a real ObjectId)
        if request.clinical_record_id and len(request.clinical_record_id) == 24:
            try:
                ObjectId(request.clinical_record_id)  # validate format
                await ClinicalService.link_diagnosis(
                    request.clinical_record_id,
                    diagnosis_doc["_id"]
                )
            except Exception:
                pass  # skip linking if record_id is invalid

        return DiagnosisResult(**diagnosis_doc)

    except Exception as e:
        error_msg = f"Prediction failed: {str(e)}"
        tb = traceback.format_exc()
        print(f"WARNING: {error_msg}")
        print(tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.post("/refine-symptoms", response_model=DiagnosisResult, response_model_by_alias=False)
async def refine_with_symptoms(
    request: RefineWithSymptomsRequest,
    current_user: User = Depends(require_doctor)
):
    """
    Refine prediction scores based on doctor-selected follow-up symptoms.
    Computes: refined_score = confidence_percentage + (matched × symptom_weight)
    """
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database

    diagnoses = Database.get_collection("diagnoses")

    # Get original diagnosis
    try:
        original = await diagnoses.find_one({"_id": ObjectId(request.diagnosis_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original diagnosis not found"
        )

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original diagnosis not found"
        )

    # Refine predictions using selected symptoms
    predictions = original.get("predictions", [])
    refined = refine_predictions(predictions, request.selected_symptoms)

    # Recompute follow-up symptoms after refinement
    followup_symptoms = get_followup_symptoms(refined)

    # Create refined diagnosis document
    refined_doc = {
        "patient_id": original["patient_id"],
        "clinical_record_id": original.get("clinical_record_id"),
        "predictions": refined,
        "top_prediction": refined[0] if refined else None,
        "follow_up_questions": [],
        "followup_symptoms": followup_symptoms,
        "confidence_score": min(1.0, max(0.0, (refined[0]["symptom_confidence"] / 100.0))) if refined else 0.5,
        "requires_more_info": len(followup_symptoms) > 0,
        "ai_notes": f"Refined with {len(request.selected_symptoms)} additional symptom(s) selected by doctor.",
        "model_version": "xgboost-1.0.0",
        "created_at": datetime.utcnow(),
        "previous_diagnosis_id": request.diagnosis_id
    }

    result = await diagnoses.insert_one(refined_doc)
    refined_doc["_id"] = str(result.inserted_id)

    return DiagnosisResult(**refined_doc)


@router.post("/finalize", response_model=DiagnosisResult, response_model_by_alias=False)
async def finalize_diagnosis(
    request: FinalDiagnosisRequest,
    current_user: User = Depends(require_doctor)
):
    """Doctor confirms the final disease diagnosis."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database

    diagnoses = Database.get_collection("diagnoses")

    try:
        original = await diagnoses.find_one({"_id": ObjectId(request.diagnosis_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )

    # Update the diagnosis with the doctor's final choice
    await diagnoses.update_one(
        {"_id": ObjectId(request.diagnosis_id)},
        {"$set": {"final_diagnosis": request.selected_disease}}
    )

    original["_id"] = str(original["_id"])
    original["final_diagnosis"] = request.selected_disease

    return DiagnosisResult(**original)


@router.post("/refine", response_model=DiagnosisResult, response_model_by_alias=False)
async def refine_diagnosis(
    request: DiagnosisRefineRequest,
    current_user: User = Depends(require_doctor)
):
    """Legacy: Refine diagnosis with additional information."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database

    diagnoses = Database.get_collection("diagnoses")

    try:
        original = await diagnoses.find_one({"_id": ObjectId(request.diagnosis_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original diagnosis not found"
        )

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original diagnosis not found"
        )

    predictions = original.get("predictions", [])
    if predictions:
        predictions[0]["probability"] = min(0.98, predictions[0]["probability"] + 0.1)
        predictions[0]["confidence"] = "high"

    refined_doc = {
        "patient_id": original["patient_id"],
        "clinical_record_id": original.get("clinical_record_id"),
        "predictions": predictions,
        "top_prediction": predictions[0] if predictions else None,
        "follow_up_questions": [],
        "followup_symptoms": [],
        "confidence_score": min(1.0, max(0.0, predictions[0]["probability"])) if predictions else 0.5,
        "requires_more_info": False,
        "ai_notes": f"Refined diagnosis based on answers to {len(request.answers)} follow-up questions.",
        "model_version": "xgboost-1.0.0",
        "created_at": datetime.utcnow(),
        "previous_diagnosis_id": request.diagnosis_id
    }

    result = await diagnoses.insert_one(refined_doc)
    refined_doc["_id"] = str(result.inserted_id)

    return DiagnosisResult(**refined_doc)


@router.get("/{diagnosis_id}", response_model=DiagnosisResult, response_model_by_alias=False)
async def get_diagnosis(
    diagnosis_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get diagnosis by ID."""
    from bson import ObjectId
    from ..database import Database

    diagnoses = Database.get_collection("diagnoses")

    try:
        diagnosis = await diagnoses.find_one({"_id": ObjectId(diagnosis_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )

    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )

    diagnosis["_id"] = str(diagnosis["_id"])
    return DiagnosisResult(**diagnosis)
