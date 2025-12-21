from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class VideoEmbeddingSegment(BaseModel):
    start_offset_sec: float
    end_offset_sec: float
    embedding: List[float]

class EmbeddingResponse(BaseModel):
    text_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    video_embeddings: Optional[List[VideoEmbeddingSegment]] = None
    dimension: int = Field(..., description="Dimension of the embeddings")
