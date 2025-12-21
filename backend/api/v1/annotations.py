"""
Annotation API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
from io import BytesIO
import pandas as pd
import re
import structlog
import os
import uuid
import shutil

from core.database import SessionLocal
from core.config import settings
from models.image import Image, Annotation
from models.project import Project, Dataset
from models.user import User
from models.import_job import AnnotationImportJob, ImportJobStatus
from api.v1.auth import get_current_user
from services.annotation_import_service import AnnotationImportService

logger = structlog.get_logger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class AnnotationCreate(BaseModel):
    answer_value: Optional[Any] = None
    is_skipped: bool = False
    is_flagged: bool = False
    flag_reason: Optional[str] = None

class AnnotationResponse(BaseModel):
    id: str
    image_id: str
    answer_value: Optional[Any]
    is_skipped: bool
    is_flagged: bool
    flag_reason: Optional[str]
    annotator_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class ImageWithAnnotation(BaseModel):
    id: str
    filename: str
    dataset_id: str
    has_annotation: bool
    annotation: Optional[AnnotationResponse]

class AnnotationStats(BaseModel):
    total_images: int
    annotated: int
    skipped: int
    flagged: int
    remaining: int

class ImportJobResponse(BaseModel):
    id: str
    status: ImportJobStatus
    total_rows: int
    processed_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    errors: Optional[List[dict]]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

# Endpoints
@router.get("/projects/{project_id}/datasets/{dataset_id}/annotations/stats", response_model=AnnotationStats)
async def get_annotation_stats(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get annotation statistics for a dataset"""
    # Verify access
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Count totals
    total = db.query(func.count(Image.id)).filter(Image.dataset_id == dataset_id).scalar()

    annotated = db.query(func.count(Annotation.id)).join(Image).filter(
        Image.dataset_id == dataset_id,
        Annotation.is_skipped == False
    ).scalar()

    skipped = db.query(func.count(Annotation.id)).join(Image).filter(
        Image.dataset_id == dataset_id,
        Annotation.is_skipped == True
    ).scalar()

    flagged = db.query(func.count(Annotation.id)).join(Image).filter(
        Image.dataset_id == dataset_id,
        Annotation.is_flagged == True
    ).scalar()

    return AnnotationStats(
        total_images=total,
        annotated=annotated,
        skipped=skipped,
        flagged=flagged,
        remaining=total - annotated - skipped
    )

@router.get("/projects/{project_id}/datasets/{dataset_id}/annotations/next")
async def get_next_unannotated(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get next unannotated image in dataset"""
    # Verify access
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check if dataset is ready for annotation
    if dataset.processing_status not in ['ready', 'completed']:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset is currently {dataset.processing_status}. Please wait until processing is complete before annotating."
        )

    # Find image without annotation
    image = db.query(Image).outerjoin(Annotation).filter(
        Image.dataset_id == dataset_id,
        Annotation.id == None
    ).order_by(Image.uploaded_at.asc()).first()

    if not image:
        return {"image": None, "message": "All images annotated"}

    return {
        "image": {
            "id": str(image.id),
            "filename": image.filename,
            "dataset_id": str(image.dataset_id)
        }
    }

@router.get("/projects/{project_id}/datasets/{dataset_id}/images/{image_id}/annotation")
async def get_annotation(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get annotation for a specific image"""
    image = db.query(Image).filter(
        Image.id == image_id,
        Image.dataset_id == dataset_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not image.annotation:
        return {"annotation": None}

    ann = image.annotation
    return {
        "annotation": {
            "id": str(ann.id),
            "image_id": str(ann.image_id),
            "answer_value": ann.answer_value,
            "is_skipped": ann.is_skipped,
            "is_flagged": ann.is_flagged,
            "flag_reason": ann.flag_reason,
            "annotator_id": str(ann.annotator_id) if ann.annotator_id else None,
            "created_at": ann.created_at.isoformat(),
            "updated_at": ann.updated_at.isoformat()
        }
    }

@router.put("/projects/{project_id}/datasets/{dataset_id}/images/{image_id}/annotation")
async def save_annotation(
    project_id: str,
    dataset_id: str,
    image_id: str,
    data: AnnotationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update annotation for an image"""
    image = db.query(Image).filter(
        Image.id == image_id,
        Image.dataset_id == dataset_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Verify dataset belongs to project
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check if dataset is ready for annotation
    if dataset.processing_status not in ['ready', 'completed']:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset is currently {dataset.processing_status}. Please wait until processing is complete before annotating."
        )

    if image.annotation:
        # Update existing
        ann = image.annotation
        ann.answer_value = data.answer_value
        ann.is_skipped = data.is_skipped
        ann.is_flagged = data.is_flagged
        ann.flag_reason = data.flag_reason
        ann.annotator_id = current_user.id
    else:
        # Create new
        ann = Annotation(
            image_id=image.id,
            answer_value=data.answer_value,
            is_skipped=data.is_skipped,
            is_flagged=data.is_flagged,
            flag_reason=data.flag_reason,
            annotator_id=current_user.id
        )
        db.add(ann)

    db.commit()
    db.refresh(ann)

    return {
        "id": str(ann.id),
        "image_id": str(ann.image_id),
        "answer_value": ann.answer_value,
        "is_skipped": ann.is_skipped,
        "is_flagged": ann.is_flagged,
        "flag_reason": ann.flag_reason,
        "annotator_id": str(ann.annotator_id) if ann.annotator_id else None,
        "created_at": ann.created_at.isoformat(),
        "updated_at": ann.updated_at.isoformat()
    }

@router.delete("/projects/{project_id}/datasets/{dataset_id}/images/{image_id}/annotation")
async def delete_annotation(
    project_id: str,
    dataset_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete annotation for an image"""
    image = db.query(Image).filter(
        Image.id == image_id,
        Image.dataset_id == dataset_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not image.annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(image.annotation)
    db.commit()
    return {"message": "Annotation deleted"}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe download"""
    # Remove any dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def extract_annotation_value(annotation: Annotation, question_type: str) -> str:
    """Extract annotation value as string for CSV export"""
    if not annotation or not annotation.answer_value:
        return ""

    value = annotation.answer_value.get('value')
    if value is None:
        return ""

    if question_type == 'binary':
        # Convert True/False to yes/no for readability
        return "yes" if value else "no"
    else:
        return str(value)


@router.get("/projects/{project_id}/datasets/{dataset_id}/annotations/export")
async def export_annotations(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all annotations for a dataset to CSV"""

    # Verify project exists
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get all images with annotations
    images = db.query(Image).filter(
        Image.dataset_id == dataset_id
    ).all()

    # Build CSV data
    rows = []
    for img in images:
        annotation_value = extract_annotation_value(img.annotation, project.question_type)

        rows.append({
            "image_id": str(img.id),
            "image_filename": img.filename,
            "annotation_value": annotation_value,
            "dataset_name": dataset.name
        })

    # Create CSV with pandas
    df = pd.DataFrame(rows)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project.name}_{dataset.name}_annotations_{timestamp}.csv"
    filename = sanitize_filename(filename)

    # Return as streaming response with BOM for Excel
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')  # BOM helps Excel
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/projects/{project_id}/datasets/{dataset_id}/annotations/template")
async def download_template(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a sample CSV template based on project type"""

    # Verify project exists
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Generate sample rows based on question type
    samples = []

    if project.question_type == 'binary':
        samples = [
            {
                "image_id": "",
                "image_filename": "example_image_1.jpg",
                "annotation_value": "yes",
                "dataset_name": dataset.name
            },
            {
                "image_id": "",
                "image_filename": "example_image_2.jpg",
                "annotation_value": "no",
                "dataset_name": dataset.name
            },
            {
                "image_id": "",
                "image_filename": "example_image_3.jpg",
                "annotation_value": "",
                "dataset_name": dataset.name
            }
        ]
    elif project.question_type == 'multiple_choice' and project.question_options:
        for i, option in enumerate(project.question_options[:3], 1):
            samples.append({
                "image_id": "",
                "image_filename": f"example_image_{i}.jpg",
                "annotation_value": option,
                "dataset_name": dataset.name
            })
    elif project.question_type == 'count':
        samples = [
            {
                "image_id": "",
                "image_filename": "example_image_1.jpg",
                "annotation_value": "5",
                "dataset_name": dataset.name
            },
            {
                "image_id": "",
                "image_filename": "example_image_2.jpg",
                "annotation_value": "10",
                "dataset_name": dataset.name
            }
        ]
    else:  # text
        samples = [
            {
                "image_id": "",
                "image_filename": "example_image_1.jpg",
                "annotation_value": "Sample text annotation",
                "dataset_name": dataset.name
            }
        ]

    df = pd.DataFrame(samples)

    filename = f"{project.name}_{dataset.name}_template.csv"
    filename = sanitize_filename(filename)

    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/projects/{project_id}/datasets/{dataset_id}/annotations/import")
async def start_import_job(
    project_id: str,
    dataset_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start an asynchronous annotation import job.
    Uploads file to temp storage and starts background processing.
    """
    # Verify access
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # File validation
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    # Check size by seeking end
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE/1024/1024}MB"
            )
            
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    # Save file to temp location
    try:
        # Create temp dir if not exists
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp_imports")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate safe filename
        ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{uuid.uuid4()}{ext}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    except Exception as e:
        logger.error(f"Failed to save temp file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

    # Create Job
    service = AnnotationImportService(project, dataset, db)
    job = service.create_import_job(str(current_user.id), temp_path)
    
    # Trigger background task
    # Note: We pass job.id, not the object, to avoid detached instance issues in async context
    background_tasks.add_task(service.process_import_job, str(job.id))
    
    return {"job_id": str(job.id)}


@router.get("/projects/{project_id}/datasets/{dataset_id}/annotations/import/{job_id}", response_model=ImportJobResponse)
async def get_import_job_status(
    project_id: str,
    dataset_id: str,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of an import job"""
    # Verify access (optional: check if user owns job or has project access)
    # We check project access first
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id, 
        Dataset.project_id == project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    job = db.query(AnnotationImportJob).filter(
        AnnotationImportJob.id == job_id,
        AnnotationImportJob.dataset_id == dataset_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "id": str(job.id),
        "status": job.status,
        "total_rows": job.total_rows,
        "processed_rows": job.processed_rows,
        "created_count": job.created_count,
        "updated_count": job.updated_count,
        "skipped_count": job.skipped_count,
        "error_count": job.error_count,
        "errors": job.errors,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at
    }
