"""
Patient and owner models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Species(str, Enum):
    """Supported animal species."""
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RABBIT = "rabbit"
    HAMSTER = "hamster"
    GUINEA_PIG = "guinea_pig"
    FISH = "fish"
    REPTILE = "reptile"
    HORSE = "horse"
    CATTLE = "cattle"
    GOAT = "goat"
    SHEEP = "sheep"
    PIG = "pig"
    POULTRY = "poultry"
    OTHER = "other"


class Owner(BaseModel):
    """Pet owner information."""
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    address: Optional[str] = None


class PatientBase(BaseModel):
    """Base patient model."""
    name: str = Field(..., min_length=1, max_length=100, description="Pet name")
    species: Species
    breed: Optional[str] = Field(None, max_length=100)
    weight_kg: float = Field(..., gt=0, le=5000, description="Weight in kilograms")
    age_months: int = Field(..., ge=0, le=600, description="Age in months")
    sex: Optional[str] = Field(None, pattern="^(male|female|unknown)$")
    color: Optional[str] = None
    microchip_id: Optional[str] = None
    medical_history: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    owner: Owner


class PatientCreate(PatientBase):
    """Patient creation model."""
    pass


class PatientUpdate(BaseModel):
    """Patient update model (all fields optional)."""
    name: Optional[str] = None
    weight_kg: Optional[float] = None
    age_months: Optional[int] = None
    sex: Optional[str] = None
    color: Optional[str] = None
    medical_history: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    owner: Optional[Owner] = None


class Patient(PatientBase):
    """Patient response model."""
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
