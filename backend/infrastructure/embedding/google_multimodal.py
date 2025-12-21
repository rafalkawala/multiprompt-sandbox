import os
import structlog
import asyncio
from typing import Optional, List
from functools import partial
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel

# Video support is optional - not available in all vertexai versions
try:
    from vertexai.vision_models import Video, VideoSegmentConfig
except ImportError:
    Video = None
    VideoSegmentConfig = None

from core.interfaces.embedding import IEmbeddingProvider
from core.domain.embedding.schema import EmbeddingResponse, VideoEmbeddingSegment

logger = structlog.get_logger(__name__)

class GoogleMultimodalEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT_ID')
        self.location = location or os.environ.get('VERTEX_AI_LOCATION', 'us-central1')

        if not self.project_id:
             logger.warning("vertex_ai_project_id_not_found", message="Vertex AI initialization might fail if not running in an environment with default credentials project set")

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
        dimension: Optional[int] = None,
        video_segment_config: Optional[dict] = None
    ) -> EmbeddingResponse:
        """
        Generates embeddings using Google Vertex AI Multimodal Embedding Model.
        """

        try:
            model = MultiModalEmbeddingModel.from_pretrained(model_name)

            image = None
            if image_path:
                if image_path.startswith("gs://"):
                    # Use constructor for explicit GCS handling if needed,
                    # though load_from_file also supports it.
                    # Explicit is better for clarity.
                    image = Image(gcs_uri=image_path)
                else:
                    image = Image.load_from_file(image_path)
            elif image_bytes:
                image = Image(image_bytes)

            video = None
            if video_path:
                if video_path.startswith("gs://"):
                    video = Video(gcs_uri=video_path)
                else:
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

            # Use 1408 as default if not specified for Google's model
            target_dimension = dimension if dimension is not None else 1408

            loop = asyncio.get_running_loop()

            func = partial(
                model.get_embeddings,
                image=image,
                video=video,
                contextual_text=text,
                dimension=target_dimension,
                video_segment_config=vsc
            )

            embeddings = await loop.run_in_executor(None, func)

            response = EmbeddingResponse(dimension=target_dimension)

            if embeddings.text_embedding:
                response.text_embedding = embeddings.text_embedding

            if embeddings.image_embedding:
                response.image_embedding = embeddings.image_embedding

            if embeddings.video_embeddings:
                response.video_embeddings = [
                    VideoEmbeddingSegment(
                        start_offset_sec=ve.start_offset_sec,
                        end_offset_sec=ve.end_offset_sec,
                        embedding=ve.embedding
                    )
                    for ve in embeddings.video_embeddings
                ]

            return response

        except Exception as e:
            logger.error("embedding_generation_failed", model_name=model_name, error=str(e), exc_info=True)
            raise
