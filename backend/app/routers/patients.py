"""
Patient management API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Query

from ..models.patient import Patient, PatientCreate, PatientUpdate
from ..models.user import User
from ..services.patient_service import PatientService
from .dependencies import get_current_user, require_staff

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: User = Depends(require_staff)
):
    """Register a new patient."""
    patient = await PatientService.create_patient(patient_data)
    return patient


@router.get("/", response_model=List[Patient])
async def search_patients(
    q: Optional[str] = Query(None, description="Search by name or owner"),
    species: Optional[str] = Query(None, description="Filter by species"),
    phone: Optional[str] = Query(None, description="Filter by owner phone"),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user)
):
    """Search patients with filters."""
    patients = await PatientService.search_patients(
        query=q,
        species=species,
        owner_phone=phone,
        limit=limit
    )
    return patients


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get patient by ID."""
    patient = await PatientService.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    return patient


@router.put("/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: str,
    updates: PatientUpdate,
    current_user: User = Depends(require_staff)
):
    """Update patient information."""
    patient = await PatientService.update_patient(patient_id, updates)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    current_user: User = Depends(require_staff)
):
    """Delete patient record."""
    deleted = await PatientService.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )


@router.get("/{patient_id}/history")
async def get_patient_history(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get patient's clinical history."""
    # First verify patient exists
    patient = await PatientService.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    history = await PatientService.get_patient_history(patient_id)
    return {"patient_id": patient_id, "records": history}
