"""
Gemini Pro Vision service for image analysis
"""
import google.generativeai as genai
from typing import Optional
import base64
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Gemini Pro Vision API"""

    def __init__(self):
        """Initialize Gemini service with API key"""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe this image in detail",
        mime_type: str = "image/jpeg"
    ) -> dict:
        """
        Analyze an image using Gemini Pro Vision

        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            mime_type: Image MIME type

        Returns:
            Analysis result with description and labels
        """
        try:
            # Create image part
            image_part = {
                "mime_type": mime_type,
                "data": base64.b64encode(image_data).decode()
            }

            # Generate content
            response = await self._generate_content_async(
                [prompt, image_part]
            )

            # Extract description
            description = response.text

            # Extract potential labels (basic implementation)
            # You can enhance this with more sophisticated label extraction
            labels = self._extract_labels(description)

            return {
                "description": description,
                "labels": labels,
                "confidence": None  # Gemini doesn't provide confidence scores directly
            }

        except Exception as e:
            logger.error(f"Gemini image analysis failed: {str(e)}", exc_info=True)
            raise

    async def _generate_content_async(self, contents):
        """
        Generate content asynchronously
        Note: google-generativeai doesn't have async support yet,
        so we'll use a thread pool for now
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            executor,
            self.model.generate_content,
            contents
        )

        return response

    def _extract_labels(self, description: str) -> list[str]:
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
