"""
Image analysis endpoints using Gemini Pro Vision
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import base64

from core.config import settings
from api.v1.auth import get_current_user
from models.user import User
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageAnalysisResponse(BaseModel):
    """Response model for image analysis"""
    description: str
    labels: list[str]
    confidence: Optional[float] = None

def extract_labels(description: str) -> list[str]:
    """
    Extract potential labels from description
    This is a simple implementation - can be enhanced
    """
    # Basic keyword extraction
    # In production, you might want to use NLP techniques or another model
    common_objects = [
        "person", "people", "car", "building", "tree", "animal",
        "dog", "cat", "food", "nature", "urban", "indoor", "outdoor"
    ]

    description_lower = description.lower()
    found_labels = [
        obj for obj in common_objects
        if obj in description_lower
    ]

    return found_labels[:5]  # Return top 5 labels

@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form("Describe this image in detail"),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze an image using Gemini Pro Vision

    Args:
        file: Image file to analyze
        prompt: Custom prompt for image analysis
        current_user: Authenticated user

    Returns:
        Image analysis result with description and labels
    """
    try:
        # Validate file type
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {settings.ALLOWED_IMAGE_TYPES}"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes"
            )

        # Analyze image using LLM Service
        llm_service = get_llm_service()
        
        image_b64 = base64.b64encode(content).decode('utf-8')
        
        text, _ = await llm_service.generate_content(
            provider_name="gemini",
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
            prompt=prompt,
            image_data=image_b64,
            mime_type=file.content_type
        )

        labels = extract_labels(text)

        return {
            "description": text,
            "labels": labels,
            "confidence": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def image_service_health():
    """Check if image service is healthy"""
    return {"status": "healthy", "service": "images"}