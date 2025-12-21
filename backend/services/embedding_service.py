import structlog
from typing import Optional, List
from functools import lru_cache
from core.retry_utils import get_retry_decorator
from core.domain.embedding.schema import EmbeddingResponse
from infrastructure.embedding.google_multimodal import GoogleMultimodalEmbeddingProvider

logger = structlog.get_logger(__name__)

class EmbeddingService:
    def __init__(self):
        # We can support multiple providers here, similar to LLMService.
        # Future providers (e.g., CLIP) can be added here.
        self._providers = {
            "google_multimodal": GoogleMultimodalEmbeddingProvider()
        }
        self._default_provider = "google_multimodal"
        self._default_model = "multimodalembedding@001"

    @get_retry_decorator()
    async def generate_embeddings(
        self,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        video_path: Optional[str] = None,
        video_bytes: Optional[bytes] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None,
        video_segment_config: Optional[dict] = None
    ) -> EmbeddingResponse:
        """
        Generate embeddings for the provided input(s).

        Args:
            text: Text to embed.
            image_path: Path to the image (local or GCS).
            image_bytes: Raw bytes of the image.
            video_path: Path to the video (local or GCS).
            video_bytes: Raw bytes of the video.
            provider_name: Name of the provider to use (default: google_multimodal).
            model_name: Name of the model to use (default: multimodalembedding@001).
            dimension: Output dimension (e.g. 128, 256, 512, 1408).
            video_segment_config: Configuration for video segments.

        Returns:
             EmbeddingResponse with embeddings.
        """
        provider_key = provider_name or self._default_provider
        provider = self._providers.get(provider_key)

        if not provider:
            raise ValueError(f"Unknown embedding provider: {provider_key}")

        model = model_name or self._default_model

        return await provider.generate_embeddings(
            model_name=model,
            text=text,
            image_path=image_path,
            image_bytes=image_bytes,
            video_path=video_path,
            video_bytes=video_bytes,
            dimension=dimension,
            video_segment_config=video_segment_config
        )

@lru_cache()
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
