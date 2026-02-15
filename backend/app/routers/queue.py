"""
Queue and token management API routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends

from ..models.queue import (
    QueueToken, 
    QueueTokenCreate, 
    QueueDisplay, 
    QueueStatus,
    QueueCallRequest,
    QueueUpdateRequest
)
from ..models.user import User, UserRole
from ..services.queue_service import QueueService
from .dependencies import get_current_user, require_staff, require_doctor

router = APIRouter(prefix="/queue", tags=["Queue & Tokens"])


@router.post("/tokens", response_model=QueueToken, response_model_by_alias=False, status_code=status.HTTP_201_CREATED)
async def issue_token(
    token_data: QueueTokenCreate,
    current_user: User = Depends(require_staff)
):
    """Issue a new queue token for a patient."""
    try:
        token = await QueueService.issue_token(token_data, current_user.id)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/display", response_model=QueueDisplay, response_model_by_alias=False)
async def get_queue_display(current_user: User = Depends(get_current_user)):
    """Get current queue status for dashboard display."""
    return await QueueService.get_queue_display()


@router.post("/call", response_model=QueueToken, response_model_by_alias=False)
async def call_next_patient(
    request: Optional[QueueCallRequest] = None,
    current_user: User = Depends(require_doctor)
):
    """Call the next patient or a specific token."""
    token_id = request.token_id if request else None
    token = await QueueService.call_next(current_user.id, token_id)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients waiting in queue"
        )
    
    return token


@router.get("/tokens/{token_id}", response_model=QueueToken, response_model_by_alias=False)
async def get_token(
    token_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get token by ID."""
    token = await QueueService.get_token(token_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    return token


@router.get("/tokens/number/{token_number}", response_model=QueueToken, response_model_by_alias=False)
async def get_token_by_number(
    token_number: str,
    current_user: User = Depends(get_current_user)
):
    """Get token by token number (e.g., VET-001)."""
    token = await QueueService.get_token_by_number(token_number)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    return token


@router.put("/tokens/{token_id}/status", response_model=QueueToken, response_model_by_alias=False)
async def update_token_status(
    token_id: str,
    request: QueueUpdateRequest,
    current_user: User = Depends(require_doctor)
):
    """Update token status."""
    token = await QueueService.update_token_status(
        token_id, 
        request.status,
        request.notes
    )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    return token


@router.get("/my-active")
async def get_my_active_tokens(current_user: User = Depends(require_doctor)):
    """Get doctor's currently active (called/in-progress) tokens."""
    tokens = await QueueService.get_doctor_active_tokens(current_user.id)
    return {"tokens": [t.model_dump(by_alias=False) for t in tokens]}
