"""
Voice upload and transcription API routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime

from ..models.user import User
from ..services.voice_service import voice_service
from ..database import Database
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/voice", tags=["Voice Transcription"])


class AudioMetadata(BaseModel):
    """Audio file metadata response."""
    audio_id: str
    audio_path: str
    filename: str
    file_size: int
    duration_seconds: float
    uploaded_at: str
    status: str
    transcription: Optional[dict] = None


class TranscriptionResponse(BaseModel):
    """Voice transcription response."""
    audio_id: str
    transcription: str
    language: str
    extracted_symptoms: list
    confidence: float
    word_count: int
    transcribed_at: str
    is_demo: Optional[bool] = False


@router.post("/upload", response_model=AudioMetadata, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(default=None, description="Additional notes about the recording"),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a voice recording for transcription.
    
    Supported audio formats:
    - WAV, MP3, M4A, OGG, WebM, FLAC
    
    Maximum file size: 25MB
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save audio
        metadata = await voice_service.save_audio(
            file_content=content,
            filename=file.filename
        )
        
        # Store in database
        audio_collection = Database.get_collection("audio")
        db_doc = {
            **metadata,
            "notes": notes,
            "uploaded_by": current_user.id
        }
        await audio_collection.insert_one(db_doc)
        
        return AudioMetadata(**metadata)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio: {str(e)}"
        )


@router.post("/transcribe/{audio_id}", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio_id: str,
    language: str = "en",
    current_user: User = Depends(require_doctor)
):
    """
    Transcribe an uploaded audio file using Whisper AI.
    
    Returns:
    - Full transcription text
    - Extracted veterinary symptoms
    - Confidence score
    
    Note: First transcription may take longer as the Whisper model loads.
    """
    # Get audio from database
    audio_collection = Database.get_collection("audio")
    audio = await audio_collection.find_one({"audio_id": audio_id})
    
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    try:
        # Run transcription
        transcription = await voice_service.transcribe(
            audio_path=audio["audio_path"],
            language=language
        )
        
        # Update database with transcription
        await audio_collection.update_one(
            {"audio_id": audio_id},
            {
                "$set": {
                    "transcription": transcription,
                    "status": "transcribed",
                    "transcribed_at": datetime.utcnow()
                }
            }
        )
        
        return TranscriptionResponse(
            audio_id=audio_id,
            **transcription
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )


@router.get("/{audio_id}", response_model=AudioMetadata)
async def get_audio(
    audio_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get audio metadata and transcription results."""
    audio_collection = Database.get_collection("audio")
    audio = await audio_collection.find_one({"audio_id": audio_id})
    
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )
    
    return AudioMetadata(
        audio_id=audio["audio_id"],
        audio_path=audio["audio_path"],
        filename=audio["filename"],
        file_size=audio["file_size"],
        duration_seconds=audio["duration_seconds"],
        uploaded_at=audio["uploaded_at"],
        status=audio.get("status", "uploaded"),
        transcription=audio.get("transcription")
    )


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
    audio_id: str,
    current_user: User = Depends(require_doctor)
):
    """Delete an uploaded audio file."""
    deleted = await voice_service.delete_audio(audio_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )


@router.get("/", response_model=list)
async def list_audio(
    patient_id: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """List uploaded audio files with optional filters."""
    audio_collection = Database.get_collection("audio")
    
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    
    cursor = audio_collection.find(query).sort("uploaded_at", -1).limit(limit)
    results = []
    
    async for audio in cursor:
        results.append({
            "audio_id": audio["audio_id"],
            "filename": audio["filename"],
            "duration_seconds": audio["duration_seconds"],
            "uploaded_at": audio["uploaded_at"],
            "status": audio.get("status", "uploaded"),
            "has_transcription": "transcription" in audio
        })
    
    return results
