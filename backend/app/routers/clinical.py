"""
Clinical records API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends

from ..models.clinical import ClinicalRecord, ClinicalRecordCreate
from ..models.user import User
from ..services.clinical_service import ClinicalService
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/clinical", tags=["Clinical Records"])


@router.post("/records", response_model=ClinicalRecord, response_model_by_alias=False, status_code=status.HTTP_201_CREATED)
async def create_clinical_record(
    record_data: ClinicalRecordCreate,
    current_user: User = Depends(require_doctor)
):
    """Create a new clinical record for a patient visit."""
    record = await ClinicalService.create_record(record_data, current_user.id)
    return record


@router.get("/records/{record_id}", response_model=ClinicalRecord, response_model_by_alias=False)
async def get_clinical_record(
    record_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get clinical record by ID."""
    record = await ClinicalService.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical record not found"
        )
    return record


@router.put("/records/{record_id}", response_model=ClinicalRecord, response_model_by_alias=False)
async def update_clinical_record(
    record_id: str,
    updates: dict,
    current_user: User = Depends(require_doctor)
):
    """Update clinical record."""
    record = await ClinicalService.update_record(record_id, updates)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical record not found"
        )
    return record


@router.post("/records/{record_id}/complete", response_model=ClinicalRecord, response_model_by_alias=False)
async def complete_clinical_record(
    record_id: str,
    current_user: User = Depends(require_doctor)
):
    """Mark clinical record as completed."""
    record = await ClinicalService.complete_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical record not found"
        )
    return record


@router.get("/patient/{patient_id}/records", response_model=List[ClinicalRecord], response_model_by_alias=False)
async def get_patient_records(
    patient_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get all clinical records for a patient."""
    records = await ClinicalService.get_patient_records(patient_id, limit)
    return records


@router.get("/my-records", response_model=List[ClinicalRecord], response_model_by_alias=False)
async def get_my_records(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_doctor)
):
    """Get current doctor's clinical records."""
    records = await ClinicalService.get_doctor_records(
        current_user.id, 
        status=status,
        limit=limit
    )
    return records
