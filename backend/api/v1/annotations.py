"""
Annotation API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime

from core.database import SessionLocal
from models.image import Image, Annotation
from models.project import Project, Dataset
from models.user import User
from api.v1.auth import get_current_user

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

    # Find image without annotation
    image = db.query(Image).outerjoin(Annotation).filter(
        Image.dataset_id == dataset_id,
        Annotation.id == None
    ).first()

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
