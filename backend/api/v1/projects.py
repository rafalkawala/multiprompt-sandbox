"""
Project management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import structlog

from models.user import User
from api.deps import get_db, require_write_access, get_current_user
from services.project_service import ProjectService

logger = structlog.get_logger(__name__)

router = APIRouter()


# Pydantic models
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


@router.get("", response_model=List[ProjectListResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects (visible to all authenticated users)"""
    project_service = ProjectService(db)
    projects = project_service.list_projects()

    return [
        ProjectListResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            question_type=p.question_type,
            created_at=p.created_at,
            updated_at=p.updated_at,
            dataset_count=len(p.datasets) if p.datasets else 0,
            created_by=CreatorInfo(
                id=str(p.created_by.id),
                email=p.created_by.email,
                name=p.created_by.name
            )
        )
        for p in projects
    ]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Create a new project (requires write access)"""
    project_service = ProjectService(db)
    project = project_service.create_project(project_data, current_user)

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        question_text=project.question_text,
        question_type=project.question_type,
        question_options=project.question_options,
        created_by_id=str(project.created_by_id),
        created_at=project.created_at,
        updated_at=project.updated_at,
        dataset_count=0,
        datasets=[]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by ID (visible to all authenticated users)"""
    project_service = ProjectService(db)
    project = project_service.get_project(project_id)

    datasets = [
        DatasetResponse(
            id=str(d.id),
            name=d.name,
            created_at=d.created_at,
            image_count=len(d.images) if d.images else 0
        )
        for d in project.datasets
    ]

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        question_text=project.question_text,
        question_type=project.question_type,
        question_options=project.question_options,
        created_by_id=str(project.created_by_id),
        created_at=project.created_at,
        updated_at=project.updated_at,
        dataset_count=len(datasets),
        datasets=datasets
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Update project (requires write access, owner can edit their own projects)"""
    project_service = ProjectService(db)
    project = project_service.update_project(project_id, project_data, current_user)

    datasets = [
        DatasetResponse(
            id=str(d.id),
            name=d.name,
            created_at=d.created_at,
            image_count=len(d.images) if d.images else 0
        )
        for d in project.datasets
    ]

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        question_text=project.question_text,
        question_type=project.question_type,
        question_options=project.question_options,
        created_by_id=str(project.created_by_id),
        created_at=project.created_at,
        updated_at=project.updated_at,
        dataset_count=len(datasets),
        datasets=datasets
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Delete project and all its datasets/images (requires write access, owner only)"""
    project_service = ProjectService(db)
    project_name = project_service.delete_project(project_id, current_user)

    return {"message": f"Project '{project_name}' deleted successfully"}
