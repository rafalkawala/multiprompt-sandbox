from abc import ABC, abstractmethod
from typing import List, Optional, Union

class IEmbeddingProvider(ABC):
    """Abstract interface for Embedding providers."""

    @abstractmethod
    async def generate_embeddings(
        self,
        model_name: str,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        video_path: Optional[str] = None,
        video_bytes: Optional[bytes] = None,
        dimension: int = 1408,
        video_segment_config: Optional[dict] = None
    ) -> dict:
        """
        Generates embeddings from the model.

        Args:
            model_name: Name of the model to use.
            text: Text to embed.
            image_path: Path to the image (local or GCS).
            image_bytes: Raw bytes of the image.
            video_path: Path to the video (local or GCS).
            video_bytes: Raw bytes of the video.
            dimension: Output dimension (128, 256, 512, 1408).
            video_segment_config: Configuration for video segments (start_offset_sec, end_offset_sec, interval_sec).

        Returns:
            A dictionary containing embeddings:
            {
                "text_embedding": List[float],
                "image_embedding": List[float],
                "video_embeddings": List[dict] # [{start, end, embedding}]
            }
        """
        pass
