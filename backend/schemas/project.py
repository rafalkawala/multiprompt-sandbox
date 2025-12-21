from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    question_text: str
    question_type: str
    question_options: Optional[List[str]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    question_options: Optional[List[str]] = None


class DatasetResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    image_count: int

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    question_text: str
    question_type: str
    question_options: Optional[List[str]]
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    dataset_count: int
    datasets: Optional[List[DatasetResponse]] = None

    class Config:
        from_attributes = True


class CreatorInfo(BaseModel):
    id: str
    email: str
    name: Optional[str]

class ProjectListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    question_type: str
    created_at: datetime
    updated_at: datetime
    dataset_count: int
    created_by: CreatorInfo

    class Config:
        from_attributes = True
