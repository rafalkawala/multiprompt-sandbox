"""
Dataset and image management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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

from core.database import SessionLocal
from core.config import settings
from models.project import Project, Dataset
from models.image import Image
from models.user import User
from api.v1.auth import get_current_user

# Import Storage Service
from services.storage_service import get_storage_provider
from core.interfaces.storage import IStorageProvider

# Import Image Utilities
from core.image_utils import generate_thumbnail

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

    # Delete image files
    storage = get_storage_provider()
    for image in dataset.images:
        try:
            await storage.delete(image.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete image file {image.storage_path}: {e}")

    dataset_name = dataset.name
    db.delete(dataset)
    db.commit()

    logger.info(f"Deleted dataset: {dataset_name}")

    return {"message": f"Dataset '{dataset_name}' deleted successfully"}


@router.post("/{project_id}/datasets/{dataset_id}/images", response_model=UploadResponse)
async def upload_images(
    project_id: str,
    dataset_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """
    Upload images to a dataset (requires write access)

    Returns uploaded images with error details for any rejected files.
    """

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
    storage = get_storage_provider()
    
    # Standardize path structure: projects/{proj}/datasets/{dataset}/{uuid}
    storage_prefix = f"projects/{project_id}/datasets/{dataset_id}"

    errors = []

    try:
        for file in files:
            try:
                # Validate file type (checks both MIME type and extension)
                if not is_valid_image_file(file.filename, file.content_type):
                    # Get file extension for better error message
                    _, ext = os.path.splitext(file.filename)
                    if ext:
                        error_msg = f"Invalid file extension '{ext}' (allowed: .jpg, .jpeg, .png, .gif, .webp)"
                    else:
                        error_msg = f"No file extension (allowed: .jpg, .jpeg, .png, .gif, .webp)"
                    errors.append(f"{file.filename}: {error_msg}")
                    logger.warning(f"Skipping {file.filename}: {error_msg} (MIME type: {file.content_type})")
                    await file.close()
                    continue

                # Generate unique filename
                ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{uuid.uuid4()}{ext}"
                storage_path = f"{storage_prefix}/{unique_filename}"

                # Read file bytes once for both thumbnail and storage
                file_bytes = await file.read()
                file_size = len(file_bytes)

                # Generate thumbnail
                try:
                    thumbnail_bytes = generate_thumbnail(file_bytes)
                    logger.info(f"Generated thumbnail for {file.filename}: {len(thumbnail_bytes)} bytes")
                except Exception as thumb_error:
                    # If thumbnail generation fails, the file is likely corrupted or not a valid image
                    logger.warning(f"Failed to generate thumbnail for {file.filename}: {str(thumb_error)}")
                    errors.append(f"{file.filename}: Corrupted or invalid image file (thumbnail generation failed)")
                    await file.close()
                    continue

                # Create BytesIO object for storage upload (avoids file seek issues)
                file_obj = BytesIO(file_bytes)

                # Upload using storage provider
                uploaded_path, _ = await storage.upload(file_obj, storage_path)

                # Create database record with thumbnail
                image = Image(
                    dataset_id=dataset_id,
                    filename=file.filename,
                    storage_path=uploaded_path,
                    file_size=file_size,
                    thumbnail_data=thumbnail_bytes,
                    uploaded_by_id=current_user.id
                )
                db.add(image)
                uploaded_images.append(image)
                logger.info(f"Successfully uploaded {file.filename} ({file_size} bytes)")
                await file.close()

            except HTTPException as he:
                # Propagate HTTP exceptions (e.g. file too large)
                errors.append(f"{file.filename}: {he.detail}")
                await file.close()
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {str(e)}", exc_info=True)
                errors.append(f"{file.filename}: {str(e)}")
                await file.close()
            finally:
                # Ensure file is closed
                await file.close()

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
            # All uploads failed - return 400 with all error details
            error_msg = "\n".join(errors) if errors else "No valid images to upload"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        logger.info(f"Successfully uploaded {len(uploaded_images)} of {len(files)} images to dataset: {dataset.name}")

        # Build response with images and any errors
        images_response = [
            ImageResponse(
                id=str(img.id),
                filename=img.filename,
                file_size=img.file_size,
                uploaded_at=img.uploaded_at.isoformat()
            )
            for img in uploaded_images
        ]

        # Build summary message
        summary = f"Successfully uploaded {len(uploaded_images)} of {len(files)} images"
        if errors:
            summary += f" ({len(errors)} failed)"

        return UploadResponse(
            images=images_response,
            errors=errors if errors else None,
            summary=summary
        )

    except HTTPException:
        # Re-raise HTTP exceptions
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