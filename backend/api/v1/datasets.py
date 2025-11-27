"""
Dataset and image management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Tuple
from datetime import datetime
from io import BytesIO
import logging
import os
import uuid
import shutil
import base64

from core.database import SessionLocal
from core.config import settings
from models.project import Project, Dataset
from models.image import Image, Annotation
from models.user import User
from api.v1.auth import get_current_user

from core.image_utils import generate_thumbnail

# Import Storage Service
from services.storage_service import get_storage_provider
from core.interfaces.storage import IStorageProvider

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed image extensions (with leading dot)
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.JPG', '.JPEG', '.PNG', '.GIF', '.WEBP'}

def is_valid_image_file(filename: str, content_type: str) -> bool:
    """
    Validate if file is a valid image by checking both MIME type and extension.

    Falls back to extension check if MIME type is generic (application/octet-stream).
    This handles cases where browser doesn't provide correct MIME type.
    """
    # Check MIME type if it's specific (not generic)
    if content_type and content_type in settings.ALLOWED_IMAGE_TYPES:
        return True

    # Fallback: check file extension
    _, ext = os.path.splitext(filename)
    return ext in ALLOWED_IMAGE_EXTENSIONS


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
class DatasetCreate(BaseModel):
    name: str


class ImageResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    uploaded_at: str
    thumbnail_url: Optional[str] = None
    is_annotated: bool = False
    annotation_value: Optional[dict] = None
    is_skipped: bool = False
    is_flagged: bool = False

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response for batch image upload with optional error details"""
    images: List[ImageResponse]
    errors: Optional[List[str]] = None
    summary: Optional[str] = None


class DatasetResponse(BaseModel):
    id: str
    name: str
    project_id: str
    created_at: datetime
    image_count: int
    images: Optional[List[ImageResponse]] = None

    class Config:
        from_attributes = True

@router.get("/{project_id}/datasets/{dataset_id}/images", response_model=List[ImageResponse])
async def list_images(
    project_id: str,
    dataset_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_thumbnails: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List images in a dataset with pagination, optional thumbnails, and annotation status"""

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

    # Query images with pagination and join with annotations
    query = db.query(Image).outerjoin(Annotation).filter(Image.dataset_id == dataset_id)
    
    # Order by newest first
    images = query.order_by(Image.uploaded_at.desc()).offset(skip).limit(limit).all()

    results = []
    for img in images:
        thumbnail_url = None
        if include_thumbnails and img.thumbnail_data:
            try:
                b64_data = base64.b64encode(img.thumbnail_data).decode('utf-8')
                thumbnail_url = f"data:image/jpeg;base64,{b64_data}"
            except Exception as e:
                logger.error(f"Failed to encode thumbnail for image {img.id}: {e}")

        # Check annotation status
        is_annotated = False
        annotation_value = None
        is_skipped = False
        is_flagged = False
        
        if img.annotation:
            is_annotated = True
            annotation_value = img.annotation.answer_value
            is_skipped = img.annotation.is_skipped
            is_flagged = img.annotation.is_flagged

        results.append(ImageResponse(
            id=str(img.id),
            filename=img.filename,
            file_size=img.file_size,
            uploaded_at=img.uploaded_at.isoformat(),
            thumbnail_url=thumbnail_url,
            is_annotated=is_annotated,
            annotation_value=annotation_value,
            is_skipped=is_skipped,
            is_flagged=is_flagged
        ))

    return results


@router.get("/{project_id}/datasets/{dataset_id}/images/{image_id}/url")
async def get_image_url(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get signed URL for image (for cloud) or proxy URL (for local)"""

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

    storage = get_storage_provider()
    try:
        url = await storage.get_url(image.storage_path)
        return {"url": url, "type": "signed"}
    except NotImplementedError:
        # Fallback for local storage
        return {
            "url": f"/api/v1/projects/{project_id}/datasets/{dataset_id}/images/{image_id}/file",
            "type": "proxy"
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found"
        )
    except Exception as e:
        logger.error(f"Failed to get image URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate image URL"
        )


@router.get("/{project_id}/datasets/{dataset_id}/images/{image_id}/file")
async def get_image_file(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get image file (proxy endpoint for local storage or fallback)"""

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

    storage = get_storage_provider()
    try:
        content = await storage.download(image.storage_path)
        
        # Determine content type from filename
        ext = os.path.splitext(image.filename)[1].lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'application/octet-stream')

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found"
        )
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve image from storage"
        )


@router.get("/{project_id}/datasets/{dataset_id}/images/{image_id}/thumbnail")
async def get_image_thumbnail(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get image thumbnail (256x256 JPEG stored in database)"""

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

    # Check if thumbnail exists
    if not image.thumbnail_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not available for this image"
        )

    # Return thumbnail with cache headers
    return Response(
        content=image.thumbnail_data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "Content-Length": str(len(image.thumbnail_data))
        }
    )


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

    # Delete file from storage
    storage = get_storage_provider()
    try:
        await storage.delete(image.storage_path)
    except Exception as e:
        logger.error(f"Failed to delete image file: {e}")

    filename = image.filename
    db.delete(image)
    db.commit()

    return {"message": f"Image '{filename}' deleted successfully"}