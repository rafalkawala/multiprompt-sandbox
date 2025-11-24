"""
Dataset and image management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
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


def require_write_access(current_user: User = Depends(get_current_user)) -> User:
    """Require user to have write access (not a viewer)"""
    from models.user import UserRole
    if current_user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers have read-only access. Cannot create, update, or delete resources."
        )
    return current_user


# Create local uploads directory for development
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# GCS client initialization
_gcs_client = None
_gcs_bucket = None

def get_gcs_bucket():
    """Get GCS bucket client (lazy initialization)"""
    global _gcs_client, _gcs_bucket
    if settings.GCS_BUCKET_NAME:
        if _gcs_bucket is None:
            from google.cloud import storage
            _gcs_client = storage.Client()
            _gcs_bucket = _gcs_client.bucket(settings.GCS_BUCKET_NAME)
        return _gcs_bucket
    return None

def use_gcs() -> bool:
    """Check if GCS should be used for storage"""
    return bool(settings.GCS_BUCKET_NAME)


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
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Create a new dataset in a project (requires write access)"""

    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()

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
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Delete a dataset and all its images (requires write access)"""

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

    # Delete image files from GCS or local storage
    for image in dataset.images:
        try:
            if use_gcs():
                bucket = get_gcs_bucket()
                blob = bucket.blob(image.storage_path)
                if blob.exists():
                    blob.delete()
            else:
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
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Upload images to a dataset (requires write access)"""

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

    # Determine storage location
    if use_gcs():
        bucket = get_gcs_bucket()
        gcs_prefix = f"projects/{project_id}/datasets/{dataset_id}"
    else:
        dataset_dir = os.path.join(UPLOAD_DIR, str(project_id), str(dataset_id))
        os.makedirs(dataset_dir, exist_ok=True)

    errors = []

    try:
        for file in files:
            try:
                # Validate file type
                if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
                    errors.append(f"{file.filename}: Invalid file type")
                    logger.warning(f"Skipping {file.filename}: invalid type {file.content_type}")
                    continue

                # Read file content
                content = await file.read()

                # Validate file size
                if len(content) > settings.MAX_UPLOAD_SIZE:
                    errors.append(f"{file.filename}: File too large ({len(content)} bytes)")
                    logger.warning(f"Skipping {file.filename}: too large {len(content)} bytes")
                    continue

                # Generate unique filename
                ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{uuid.uuid4()}{ext}"

                # Save file to GCS or local storage
                if use_gcs():
                    storage_path = f"{gcs_prefix}/{unique_filename}"
                    blob = bucket.blob(storage_path)
                    blob.upload_from_string(content, content_type=file.content_type)
                else:
                    storage_path = os.path.join(dataset_dir, unique_filename)
                    with open(storage_path, "wb") as f:
                        f.write(content)

                # Create database record
                image = Image(
                    dataset_id=dataset_id,
                    filename=file.filename,
                    storage_path=storage_path,
                    file_size=len(content),
                    uploaded_by_id=current_user.id
                )
                db.add(image)
                uploaded_images.append(image)
                logger.info(f"Successfully queued {file.filename} for upload")

            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {str(e)}", exc_info=True)
                errors.append(f"{file.filename}: {str(e)}")
                continue

        # Commit all successful uploads
        if uploaded_images:
            db.commit()
            logger.info(f"Committed {len(uploaded_images)} images to database")

            # Refresh to get IDs
            for img in uploaded_images:
                db.refresh(img)

        if errors:
            logger.warning(f"Upload completed with {len(errors)} errors: {errors}")

        if not uploaded_images:
            error_msg = "; ".join(errors[:5]) if errors else "No valid images to upload"
            if len(errors) > 5:
                error_msg += f" (and {len(errors) - 5} more errors)"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        logger.info(f"Successfully uploaded {len(uploaded_images)} of {len(files)} images to dataset: {dataset.name}")

        return [
            ImageResponse(
                id=str(img.id),
                filename=img.filename,
                file_size=img.file_size,
                uploaded_at=img.uploaded_at.isoformat()
            )
            for img in uploaded_images
        ]

    except HTTPException:
        # Re-raise HTTP exceptions (like the "no valid images" one)
        db.rollback()
        raise
    except Exception as e:
        # Rollback on any unexpected error
        db.rollback()
        logger.error(f"Unexpected error during image upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


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

    # Serve from GCS or local storage
    if use_gcs():
        bucket = get_gcs_bucket()
        blob = bucket.blob(image.storage_path)
        if not blob.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image file not found"
            )
        content = blob.download_as_bytes()
        # Determine content type from filename
        ext = os.path.splitext(image.filename)[1].lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'application/octet-stream')
        return Response(content=content, media_type=content_type)
    else:
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
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Delete an image (requires write access)"""

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

    # Delete file from GCS or local storage
    try:
        if use_gcs():
            bucket = get_gcs_bucket()
            blob = bucket.blob(image.storage_path)
            if blob.exists():
                blob.delete()
        else:
            if os.path.exists(image.storage_path):
                os.remove(image.storage_path)
    except Exception as e:
        logger.error(f"Failed to delete image file: {e}")

    filename = image.filename
    db.delete(image)
    db.commit()

    return {"message": f"Image '{filename}' deleted successfully"}
