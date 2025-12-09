import os
import logging
import asyncio
from typing import Optional, List
from functools import partial
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel, Video, VideoSegmentConfig
from core.interfaces.embedding import IEmbeddingProvider

logger = logging.getLogger(__name__)

class GoogleMultimodalEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT_ID')
        self.location = location or os.environ.get('VERTEX_AI_LOCATION', 'us-central1')

        if not self.project_id:
             logger.warning("Project ID not found. Vertex AI initialization might fail if not running in an environment with default credentials project set.")

        if self.project_id:
            vertexai.init(project=self.project_id, location=self.location)

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
        Generates embeddings using Google Vertex AI Multimodal Embedding Model.
        """

        try:
            # Load model (this might also block, but usually it's fast if not downloading large files,
            # and from_pretrained for vertexai models is often just configuration.
            # However, for strict non-blocking, we could also offload this).
            model = MultiModalEmbeddingModel.from_pretrained(model_name)

            image = None
            if image_path:
                image = Image.load_from_file(image_path)
            elif image_bytes:
                image = Image(image_bytes)

            video = None
            if video_path:
                video = Video.load_from_file(video_path)
            elif video_bytes:
                video = Video(video_bytes)

            vsc = None
            if video_segment_config:
                vsc = VideoSegmentConfig(
                    start_offset_sec=video_segment_config.get('start_offset_sec', 0),
                    end_offset_sec=video_segment_config.get('end_offset_sec'),
                    interval_sec=video_segment_config.get('interval_sec')
                )

            # Offload the blocking SDK call to a separate thread
            loop = asyncio.get_running_loop()

            # Use partial to pass arguments to the synchronous function
            # The get_embeddings method of the model
            func = partial(
                model.get_embeddings,
                image=image,
                video=video,
                contextual_text=text,
                dimension=dimension,
                video_segment_config=vsc
            )

            embeddings = await loop.run_in_executor(None, func)

            result = {}
            if embeddings.text_embedding:
                result["text_embedding"] = embeddings.text_embedding

            if embeddings.image_embedding:
                result["image_embedding"] = embeddings.image_embedding

            if embeddings.video_embeddings:
                result["video_embeddings"] = [
                    {
                        "start_offset_sec": ve.start_offset_sec,
                        "end_offset_sec": ve.end_offset_sec,
                        "embedding": ve.embedding
                    }
                    for ve in embeddings.video_embeddings
                ]

            return result

        except Exception as e:
            logger.error(f"Error generating embeddings with model {model_name}: {str(e)}")
            raise e
