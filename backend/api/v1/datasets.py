"""
Dataset and image management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import os
import uuid
import shutil

from core.database import SessionLocal
from core.config import settings
from models.project import Project, Dataset
from models.image import Image
from models.user import User
from api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Create uploads directory
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models
class DatasetCreate(BaseModel):
    name: str


class ImageResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    uploaded_at: str

    class Config:
        from_attributes = True


class DatasetResponse(BaseModel):
    id: str
    name: str
    project_id: str
    created_at: datetime
    image_count: int
    images: Optional[List[ImageResponse]] = None

    class Config:
        from_attributes = True


@router.post("/{project_id}/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    project_id: str,
    dataset_data: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new dataset in a project"""

    # Verify project exists and belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    dataset = Dataset(
        name=dataset_data.name,
        project_id=project_id,
        created_by_id=current_user.id
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    logger.info(f"Created dataset: {dataset.name} in project: {project.name}")

    return DatasetResponse(
        id=str(dataset.id),
        name=dataset.name,
        project_id=str(dataset.project_id),
        created_at=dataset.created_at,
        image_count=0,
        images=[]
    )


@router.get("/{project_id}/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all datasets in a project"""

    # Verify project exists and belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return [
        DatasetResponse(
            id=str(d.id),
            name=d.name,
            project_id=str(d.project_id),
            created_at=d.created_at,
            image_count=len(d.images) if d.images else 0
        )
        for d in project.datasets
    ]


@router.delete("/{project_id}/datasets/{dataset_id}")
async def delete_dataset(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a dataset and all its images"""

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Delete image files
    for image in dataset.images:
        try:
            if os.path.exists(image.storage_path):
                os.remove(image.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete image file: {e}")

    dataset_name = dataset.name
    db.delete(dataset)
    db.commit()

    logger.info(f"Deleted dataset: {dataset_name}")

    return {"message": f"Dataset '{dataset_name}' deleted successfully"}


@router.post("/{project_id}/datasets/{dataset_id}/images", response_model=List[ImageResponse])
async def upload_images(
    project_id: str,
    dataset_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload images to a dataset"""

    # Verify dataset exists
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    uploaded_images = []
    dataset_dir = os.path.join(UPLOAD_DIR, str(project_id), str(dataset_id))
    os.makedirs(dataset_dir, exist_ok=True)

    for file in files:
        # Validate file type
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            continue  # Skip invalid files

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > settings.MAX_UPLOAD_SIZE:
            continue  # Skip too large files

        # Generate unique filename
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(dataset_dir, unique_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Create database record
        image = Image(
            dataset_id=dataset_id,
            filename=file.filename,
            storage_path=file_path,
            file_size=len(content),
            uploaded_by_id=current_user.id
        )
        db.add(image)
        uploaded_images.append(image)

    db.commit()

    # Refresh to get IDs
    for img in uploaded_images:
        db.refresh(img)

    logger.info(f"Uploaded {len(uploaded_images)} images to dataset: {dataset.name}")

    return [
        ImageResponse(
            id=str(img.id),
            filename=img.filename,
            file_size=img.file_size,
            uploaded_at=img.uploaded_at.isoformat()
        )
        for img in uploaded_images
    ]


@router.get("/{project_id}/datasets/{dataset_id}/images", response_model=List[ImageResponse])
async def list_images(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all images in a dataset"""

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return [
        ImageResponse(
            id=str(img.id),
            filename=img.filename,
            file_size=img.file_size,
            uploaded_at=img.uploaded_at.isoformat()
        )
        for img in dataset.images
    ]


@router.get("/{project_id}/datasets/{dataset_id}/images/{image_id}/file")
async def get_image_file(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get image file"""

    image = db.query(Image).filter(
        Image.id == image_id,
        Image.dataset_id == dataset_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not os.path.exists(image.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found"
        )

    return FileResponse(image.storage_path, filename=image.filename)


@router.delete("/{project_id}/datasets/{dataset_id}/images/{image_id}")
async def delete_image(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an image"""

    image = db.query(Image).filter(
        Image.id == image_id,
        Image.dataset_id == dataset_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Verify project belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Delete file
    try:
        if os.path.exists(image.storage_path):
            os.remove(image.storage_path)
    except Exception as e:
        logger.error(f"Failed to delete image file: {e}")

    filename = image.filename
    db.delete(image)
    db.commit()

    return {"message": f"Image '{filename}' deleted successfully"}
