"""
Image upload and analysis API routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime

from ..models.user import User
from ..services.image_service import image_analyzer
from ..database import Database
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/images", tags=["Image Analysis"])


class ImageMetadata(BaseModel):
    """Image metadata response."""
    image_id: str
    original_path: str
    thumbnail_path: str
    image_type: str
    filename: str
    file_size: int
    width: int
    height: int
    uploaded_at: str
    analysis: Optional[dict] = None


class ImageAnalysisResponse(BaseModel):
    """Image analysis response."""
    image_id: str
    image_type: str
    detected_features: list
    suggested_conditions: list
    color_analysis: dict
    cnn_feature_summary: dict
    analyzed_at: str


@router.post("/upload", response_model=ImageMetadata, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    image_type: str = Form(default="general", description="Type: skin, eye, xray, or general"),
    body_part: Optional[str] = Form(default=None, description="Body part shown in image"),
    notes: Optional[str] = Form(default=None, description="Additional notes"),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a clinical image for analysis.
    
    Supported image types:
    - **skin**: Skin conditions, lesions, rashes
    - **eye**: Eye problems, discharge, cloudiness
    - **xray**: X-ray images (future support)
    - **general**: General clinical photos
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save image
        metadata = await image_analyzer.save_image(
            file_content=content,
            filename=file.filename,
            image_type=image_type
        )
        
        # Store in database
        images = Database.get_collection("images")
        db_doc = {
            **metadata,
            "body_part": body_part,
            "notes": notes,
            "uploaded_by": current_user.id,
            "status": "uploaded"
        }
        await images.insert_one(db_doc)
        
        return ImageMetadata(**metadata)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post("/analyze/{image_id}", response_model=ImageAnalysisResponse)
async def analyze_image(
    image_id: str,
    current_user: User = Depends(require_doctor)
):
    """
    Analyze an uploaded image using AI (MobileNetV2 transfer learning).
    
    Returns detected features and suggested veterinary conditions (skin/eye).
    """
    # Get image from database
    images = Database.get_collection("images")
    image = await images.find_one({"image_id": image_id})
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    try:
        # Run analysis
        analysis = await image_analyzer.analyze_image(
            image_path=image["original_path"],
            image_type=image["image_type"]
        )
        
        # Update database with analysis results
        await images.update_one(
            {"image_id": image_id},
            {
                "$set": {
                    "analysis": analysis,
                    "status": "analyzed",
                    "analyzed_at": datetime.utcnow()
                }
            }
        )
        
        return ImageAnalysisResponse(
            image_id=image_id,
            **analysis
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/{image_id}", response_model=ImageMetadata)
async def get_image(
    image_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get image metadata and analysis results."""
    images = Database.get_collection("images")
    image = await images.find_one({"image_id": image_id})
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return ImageMetadata(
        image_id=image["image_id"],
        original_path=image["original_path"],
        thumbnail_path=image["thumbnail_path"],
        image_type=image["image_type"],
        filename=image["filename"],
        file_size=image["file_size"],
        width=image["width"],
        height=image["height"],
        uploaded_at=image["uploaded_at"],
        analysis=image.get("analysis")
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str,
    current_user: User = Depends(require_doctor)
):
    """Delete an uploaded image."""
    deleted = await image_analyzer.delete_image(image_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )


@router.get("/", response_model=list)
async def list_images(
    patient_id: Optional[str] = None,
    image_type: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """List uploaded images with optional filters."""
    images = Database.get_collection("images")
    
    query = {}
    if patient_id:
        query["patient_id"] = patient_id
    if image_type:
        query["image_type"] = image_type
    
    cursor = images.find(query).sort("uploaded_at", -1).limit(limit)
    results = []
    
    async for image in cursor:
        results.append({
            "image_id": image["image_id"],
            "image_type": image["image_type"],
            "filename": image["filename"],
            "thumbnail_path": image["thumbnail_path"],
            "uploaded_at": image["uploaded_at"],
            "status": image.get("status", "uploaded"),
            "has_analysis": "analysis" in image
        })
    
    return results
