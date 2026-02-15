"""
Queue token models for patient management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class QueueStatus(str, Enum):
    """Token/queue status states."""
    WAITING = "waiting"
    CALLED = "called"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class QueueTokenCreate(BaseModel):
    """Create a new queue token."""
    patient_id: str
    priority: int = Field(default=0, ge=0, le=10, description="0=normal, higher=urgent")
    notes: Optional[str] = None


class QueueToken(BaseModel):
    """Queue token response model."""
    id: str = Field(..., alias="_id")
    token_number: str = Field(..., description="Display token like VET-001")
    patient_id: str
    patient_name: Optional[str] = None
    species: Optional[str] = None
    owner_name: Optional[str] = None
    status: QueueStatus = QueueStatus.WAITING
    priority: int = 0
    notes: Optional[str] = None
    issued_at: datetime
    issued_by: str  # Staff user ID
    called_at: Optional[datetime] = None
    called_by: Optional[str] = None  # Doctor user ID
    completed_at: Optional[datetime] = None
    estimated_wait_minutes: Optional[int] = None
    
    class Config:
        populate_by_name = True


class QueueDisplay(BaseModel):
    """Queue display for dashboard."""
    waiting: List[QueueToken] = []
    in_progress: List[QueueToken] = []
    total_waiting: int = 0
    average_wait_minutes: Optional[float] = None
    next_token: Optional[str] = None


class QueueCallRequest(BaseModel):
    """Request to call next patient."""
    token_id: Optional[str] = None  # Specific token, or None for next in queue


class QueueUpdateRequest(BaseModel):
    """Update token status."""
    status: QueueStatus
    notes: Optional[str] = None
