from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class DatasetSplitBase(BaseModel):
    name: str
    split_type: str  # 'random_percent', 'random_count', 'manual'
    split_value: Optional[int] = None
    excluded_split_ids: Optional[List[UUID]] = None

class DatasetSplitCreate(DatasetSplitBase):
    pass

class DatasetSplitResponse(DatasetSplitBase):
    id: UUID
    dataset_id: UUID
    image_ids: List[str]  # Or List[UUID]
    created_by_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
