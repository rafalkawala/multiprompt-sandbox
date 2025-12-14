"""
Project management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import structlog

from core.database import SessionLocal
from models.project import Project, Dataset
from models.user import User
from api.v1.auth import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter()


def require_write_access(current_user: User = Depends(get_current_user)) -> User:
    """Require user to have write access (not a viewer)"""
    from models.user import UserRole
    if current_user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers have read-only access. Cannot create, update, or delete resources."
        )
    return current_user


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    projects = db.query(Project).order_by(Project.created_at.desc()).all()

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

    # Validate question_type
    valid_types = ['binary', 'multiple_choice', 'text', 'count']
    if project_data.question_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid question_type. Must be one of: {valid_types}"
        )

    # Multiple choice requires options
    if project_data.question_type == 'multiple_choice' and not project_data.question_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question_options required for multiple_choice type"
        )

    project = Project(
        name=project_data.name,
        description=project_data.description,
        question_text=project_data.question_text,
        question_type=project_data.question_type,
        question_options=project_data.question_options,
        created_by_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info(f"Created project: {project.name} by user: {current_user.email}")

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

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

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

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Only the project owner can edit their project
    if str(project.created_by_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own projects"
        )

    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.question_text is not None:
        project.question_text = project_data.question_text
    if project_data.question_type is not None:
        valid_types = ['binary', 'multiple_choice', 'text', 'count']
        if project_data.question_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question_type. Must be one of: {valid_types}"
            )
        project.question_type = project_data.question_type
    if project_data.question_options is not None:
        project.question_options = project_data.question_options

    db.commit()
    db.refresh(project)

    logger.info(f"Updated project: {project.name}")

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

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Only the project owner can delete their project
    if str(project.created_by_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own projects"
        )

    project_name = project.name
    db.delete(project)
    db.commit()

    logger.info(f"Deleted project: {project_name}")

    return {"message": f"Project '{project_name}' deleted successfully"}
