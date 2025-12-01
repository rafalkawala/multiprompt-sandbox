"""
Dataset and image management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, BackgroundTasks
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
import asyncio

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


class BatchUploadResponse(BaseModel):
    """Response for batch upload - Phase 1 (upload to GCS)"""
    dataset_id: str
    uploaded_count: int
    failed_count: int
    processing_status: str  # 'processing', 'failed'
    errors: Optional[List[str]] = None
    message: str


class ProcessingStatusResponse(BaseModel):
    """Response for processing status polling"""
    dataset_id: str
    processing_status: str  # 'ready', 'uploading', 'processing', 'completed', 'failed'
    total_files: int
    processed_files: int
    failed_files: int
    progress_percent: float
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    errors: Optional[List[str]] = None


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


@router.post("/{project_id}/datasets/{dataset_id}/images/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_images(
    project_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """
    Batch upload images - Two-phase approach:
    Phase 1 (this endpoint): Stream files directly to GCS in parallel
    Phase 2 (background): Generate thumbnails via Cloud Tasks

    This endpoint returns immediately after uploading to GCS.
    Use the processing-status endpoint to monitor thumbnail generation progress.

    Security: Validates individual file sizes (10MB limit per file).
    Frontend should chunk batches to stay under Cloud Run's 32MB request limit.
    """

    # Validate individual file sizes (10MB limit)
    oversized_files = []
    for file in files:
        # Get file size by reading content-length header or reading the file
        file_size = 0
        if hasattr(file, 'size') and file.size:
            file_size = file.size
        else:
            # Read file to get size (will seek back to start)
            await file.seek(0)
            content = await file.read()
            file_size = len(content)
            await file.seek(0)

        if file_size > settings.MAX_UPLOAD_SIZE:
            oversized_files.append(f"{file.filename} ({file_size / (1024 * 1024):.1f}MB)")

    if oversized_files:
        error_msg = f"{len(oversized_files)} file(s) exceed {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB limit: {', '.join(oversized_files[:3])}"
        if len(oversized_files) > 3:
            error_msg += f" and {len(oversized_files) - 3} more"
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_msg
        )

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

    # Check if dataset is already being uploaded by another request
    # Allow uploads during 'processing' (background thumbnail generation) to support chunked batches
    if dataset.processing_status == 'uploading':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset is currently being uploaded. Please wait for it to complete."
        )

    logger.info(f"Starting batch upload of {len(files)} files to dataset {dataset_id}")

    # Update dataset status to 'uploading'
    # If already processing, we're adding to an existing batch (chunked upload)
    is_continuation = dataset.processing_status == 'processing'

    dataset.processing_status = "uploading"
    if not is_continuation:
        # New upload session - reset counters
        dataset.processing_started_at = datetime.utcnow()
        dataset.total_files = len(files)
        dataset.processed_files = 0
        dataset.failed_files = 0
        dataset.processing_errors = []
    else:
        # Continuing chunked upload - add to existing total
        dataset.total_files = (dataset.total_files or 0) + len(files)
        logger.info(f"Continuing chunked upload - new total: {dataset.total_files} files")

    db.commit()

    storage = get_storage_provider()
    storage_prefix = f"projects/{project_id}/datasets/{dataset_id}"

    uploaded_images = []
    errors = []

    # Semaphore for rate limiting parallel uploads
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent uploads

    async def upload_single_file(file: UploadFile) -> Optional[Image]:
        """Upload a single file to GCS and create database record"""
        async with semaphore:
            try:
                # Validate file type
                if not is_valid_image_file(file.filename, file.content_type):
                    _, ext = os.path.splitext(file.filename)
                    error_msg = f"Invalid file extension '{ext}' (allowed: .jpg, .jpeg, .png, .gif, .webp)"
                    errors.append(f"{file.filename}: {error_msg}")
                    logger.warning(f"Skipping {file.filename}: {error_msg}")
                    await file.close()
                    return None

                # Generate unique filename
                ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{uuid.uuid4()}{ext}"
                storage_path = f"{storage_prefix}/{unique_filename}"

                # Stream upload directly to GCS (no BytesIO buffering)
                uploaded_path, file_size = await storage.upload(file, storage_path)

                logger.info(f"Uploaded {file.filename} to {uploaded_path} ({file_size} bytes)")

                # Create database record with processing_status='pending'
                # Thumbnail will be generated in Phase 2
                image = Image(
                    dataset_id=dataset_id,
                    filename=file.filename,
                    storage_path=uploaded_path,
                    file_size=file_size,
                    thumbnail_data=None,  # Generated in Phase 2
                    processing_status='pending',  # Will be processed by Cloud Task
                    uploaded_by_id=current_user.id
                )

                await file.close()
                return image

            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {str(e)}", exc_info=True)
                errors.append(f"{file.filename}: {str(e)}")
                await file.close()
                return None

    try:
        # Upload all files in parallel
        results = await asyncio.gather(
            *[upload_single_file(file) for file in files],
            return_exceptions=True
        )

        # Filter out None and exceptions
        uploaded_images = [img for img in results if isinstance(img, Image)]

        # Add all images to database
        if uploaded_images:
            db.add_all(uploaded_images)
            db.commit()
            logger.info(f"Committed {len(uploaded_images)} images to database")

        # Update dataset status
        if not uploaded_images:
            # All uploads failed
            dataset.processing_status = "failed"
            dataset.processing_completed_at = datetime.utcnow()
            dataset.processing_errors = errors[:10]  # Limit to 10 errors
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All uploads failed. Errors: {'; '.join(errors[:3])}"
            )

        # Update dataset to 'processing' and enqueue Cloud Task
        dataset.processing_status = "processing"
        # Don't overwrite total_files if this is a continuation (already set in line 822)
        if not is_continuation:
            dataset.total_files = len(uploaded_images)
        db.commit()

        # Phase 2: Enqueue background processing (Cloud Tasks or local)
        # Only enqueue for the first batch - subsequent batches will be processed by the same task
        if not is_continuation:
            if settings.USE_CLOUD_TASKS:
                # Production: Use Google Cloud Tasks
                try:
                    from services.cloud_tasks_service import get_cloud_tasks_service
                    tasks_service = get_cloud_tasks_service()
                    task_name = tasks_service.enqueue_dataset_processing(project_id, dataset_id)
                    logger.info(f"Enqueued Cloud Task: {task_name}")
                except Exception as e:
                    logger.error(f"Failed to enqueue Cloud Task: {str(e)}", exc_info=True)
                    # Don't fail the request - images are uploaded, just log the error
            else:
                # Local development: Use FastAPI BackgroundTasks
                try:
                    from services.image_processing_service import ImageProcessingService
                    from core.database import SessionLocal

                    def process_in_background():
                        """Process dataset images in background thread"""
                        db_session = SessionLocal()
                        try:
                            service = ImageProcessingService()
                            import asyncio
                            asyncio.run(service.process_dataset_images(dataset_id, db_session))
                        except Exception as e:
                            logger.error(f"Background processing failed: {str(e)}", exc_info=True)
                        finally:
                            db_session.close()

                    background_tasks.add_task(process_in_background)
                    logger.info(f"Added local background task for dataset {dataset_id}")
                except Exception as e:
                    logger.error(f"Failed to enqueue background task: {str(e)}", exc_info=True)
        else:
            logger.info(f"Continuing chunked upload - processing task already queued")

        message = f"Successfully uploaded {len(uploaded_images)} of {len(files)} files to GCS. Thumbnail generation started in background."
        if errors:
            message += f" ({len(errors)} files failed)"

        return BatchUploadResponse(
            dataset_id=str(dataset_id),
            uploaded_count=len(uploaded_images),
            failed_count=len(errors),
            processing_status=dataset.processing_status,
            errors=errors if errors else None,
            message=message
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during batch upload: {str(e)}", exc_info=True)

        # Update dataset status to failed
        dataset.processing_status = "failed"
        dataset.processing_completed_at = datetime.utcnow()
        dataset.processing_errors = [str(e)]
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}"
        )


@router.get("/{project_id}/datasets/{dataset_id}/processing-status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get processing status for a dataset.
    Used by frontend to poll progress during Phase 2 (thumbnail generation).
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

    # Calculate progress percentage
    progress_percent = 0.0
    if dataset.total_files > 0:
        progress_percent = (dataset.processed_files / dataset.total_files) * 100

    return ProcessingStatusResponse(
        dataset_id=str(dataset_id),
        processing_status=dataset.processing_status,
        total_files=dataset.total_files,
        processed_files=dataset.processed_files,
        failed_files=dataset.failed_files,
        progress_percent=round(progress_percent, 2),
        processing_started_at=dataset.processing_started_at,
        processing_completed_at=dataset.processing_completed_at,
        errors=dataset.processing_errors if dataset.processing_errors else None
    )
