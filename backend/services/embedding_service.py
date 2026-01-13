import structlog
import json
import os
from typing import Optional, List, Dict
from functools import lru_cache
from core.retry_utils import get_retry_decorator
from core.domain.embedding.schema import EmbeddingResponse
from infrastructure.embedding.google_multimodal import GoogleMultimodalEmbeddingProvider

logger = structlog.get_logger(__name__)

class EmbeddingService:
    def __init__(self):
        # Initialize providers
        self._providers = {
            "google_multimodal": GoogleMultimodalEmbeddingProvider(),
            "vertex_embedding": GoogleMultimodalEmbeddingProvider() # Alias for config compatibility
        }

        # Load configuration from models.json
        self._config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")
        self._model_configs = self._load_model_configs()

        # Determine default model from config or fallback
        self._default_provider_key = "google_multimodal"
        self._default_model_name = "multimodalembedding@001"

        # Try to find a default in the config
        for model in self._model_configs:
            if model.get("provider") == "vertex_embedding":
                self._default_model_name = model.get("model_name")
                self._default_provider_key = "vertex_embedding"
                break

    def _load_model_configs(self) -> List[Dict]:
        """Load embedding model configurations from the JSON file."""
        if not os.path.exists(self._config_path):
            logger.warning(f"Embedding configuration file not found at {self._config_path}")
            return []

        try:
            with open(self._config_path, 'r') as f:
                all_models = json.load(f)
                # Filter for embedding models (provider 'vertex_embedding' or similar)
                return [m for m in all_models if "embedding" in m.get("provider", "").lower()]
        except Exception as e:
            logger.error(f"Failed to load embedding model configs: {e}")
            return []

    def get_available_models(self) -> List[Dict]:
        """Return a list of available embedding models."""
        return self._model_configs

    def _resolve_provider(self, provider_name: Optional[str], model_name: Optional[str]) -> str:
        """Resolve the internal provider key from the input name or model name."""
        if provider_name and provider_name in self._providers:
            return provider_name

        # Try to lookup model in config to find its provider
        if model_name:
            for config in self._model_configs:
                if config.get("model_name") == model_name:
                    p_name = config.get("provider")
                    if p_name in self._providers:
                        return p_name

        # Fallback to defaults if not found
        if not provider_name:
            return self._default_provider_key

        return provider_name

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
            provider_name: Name of the provider to use.
            model_name: Name of the model to use.
            dimension: Output dimension (e.g. 128, 256, 512, 1408).
            video_segment_config: Configuration for video segments.

        Returns:
             EmbeddingResponse with embeddings.
        """
        # Resolve model name
        target_model = model_name or self._default_model_name

        # Resolve provider
        target_provider_key = self._resolve_provider(provider_name, target_model)

        provider = self._providers.get(target_provider_key)

        if not provider:
            raise ValueError(f"Unknown embedding provider: {target_provider_key} (resolved from {provider_name}/{target_model})")

        return await provider.generate_embeddings(
            model_name=target_model,
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
