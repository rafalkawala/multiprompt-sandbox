"""
Image analysis endpoints using Gemini Pro Vision
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import logging

from services.gemini_service import GeminiService
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageAnalysisResponse(BaseModel):
    """Response model for image analysis"""
    description: str
    labels: list[str]
    confidence: Optional[float] = None


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form("Describe this image in detail")
):
    """
    Analyze an image using Gemini Pro Vision

    Args:
        file: Image file to analyze
        prompt: Custom prompt for image analysis

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

        # Analyze image
        gemini_service = GeminiService()
        result = await gemini_service.analyze_image(
            image_data=content,
            prompt=prompt,
            mime_type=file.content_type
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def image_service_health():
    """Check if image service is healthy"""
    return {"status": "healthy", "service": "images"}
