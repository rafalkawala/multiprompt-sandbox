"""
Labelling Jobs API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
import threading

from core.database import SessionLocal
from models.labelling_job import LabellingJob, LabellingJobRun, LabellingResult
from models.project import Project, Dataset
from models.evaluation import Evaluation, ModelConfig
from models.user import User
from api.v1.auth import get_current_user
from services.labelling_job_service import get_labelling_job_service
from services.cloud_tasks_service import get_cloud_tasks_service
from core.config import settings

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


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic schemas
class LabellingJobCreate(BaseModel):
    name: str
    project_id: str
    evaluation_id: str  # Copy prompt config from this evaluation
    gcs_folder_path: str
    frequency_minutes: int = 15
    is_active: bool = True


class LabellingJobUpdate(BaseModel):
    name: Optional[str] = None
    gcs_folder_path: Optional[str] = None
    frequency_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class LabellingJobResponse(BaseModel):
    id: str
    name: str
    project_id: str
    dataset_id: Optional[str]
    dataset_name: Optional[str]
    gcs_folder_path: str
    last_processed_timestamp: Optional[datetime]
    frequency_minutes: int
    is_active: bool
    status: str
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    total_runs: int
    total_images_processed: int
    total_images_labeled: int
    total_errors: int
    created_by_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LabellingJobRunResponse(BaseModel):
    id: str
    labelling_job_id: str
    status: str
    trigger_type: str
    images_discovered: int
    images_ingested: int
    images_labeled: int
    images_failed: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LabellingResultResponse(BaseModel):
    id: str
    labelling_job_id: str
    labelling_job_run_id: str
    image_id: str
    model_response: str
    parsed_answer: dict
    confidence_score: Optional[float]
    latency_ms: Optional[int]
    error: Optional[str]
    gcs_source_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Helper functions
def run_job_in_thread(job_id: str, trigger_type: str):
    """Run job in a separate thread with its own event loop"""
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        db = SessionLocal()
        try:
            service = get_labelling_job_service()
            loop.run_until_complete(service.run_job(job_id, db, trigger_type))
        except Exception as e:
            logger.error(f"Job execution failed: {str(e)}", exc_info=True)
        finally:
            db.close()
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


# Endpoints
@router.post("/labelling-jobs", response_model=LabellingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_labelling_job(
    job_data: LabellingJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """
    Create a new labelling job.
    Copies prompt configuration from an existing evaluation.
    Auto-creates a dedicated dataset named "Job Output: [JobName]".
    """
    # Validate project exists and user has access
    project = db.query(Project).filter(
        Project.id == job_data.project_id,
        Project.created_by_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )

    # Get evaluation to copy config from
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == job_data.evaluation_id
    ).first()

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )

    # Validate GCS path format
    if not job_data.gcs_folder_path.startswith('gs://'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GCS folder path must start with gs://"
        )

    # Create job
    job = LabellingJob(
        name=job_data.name,
        project_id=job_data.project_id,
        gcs_folder_path=job_data.gcs_folder_path,
        model_config_id=evaluation.model_config_id,
        system_message=evaluation.system_message or "",
        question_text=evaluation.question_text or project.question_text,
        frequency_minutes=job_data.frequency_minutes,
        is_active=job_data.is_active,
        status='idle',
        created_by_id=current_user.id
    )

    # Calculate next run time if active
    if job_data.is_active:
        job.next_run_at = datetime.utcnow() + timedelta(minutes=job_data.frequency_minutes)

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Created labelling job {job.id}: {job.name}")

    # Build response
    response = LabellingJobResponse(
        **job.__dict__,
        dataset_name=None
    )
    return response


@router.get("/labelling-jobs", response_model=List[LabellingJobResponse])
async def list_labelling_jobs(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all labelling jobs, optionally filtered by project"""
    query = db.query(LabellingJob).filter(
        LabellingJob.created_by_id == current_user.id
    )

    if project_id:
        query = query.filter(LabellingJob.project_id == project_id)

    jobs = query.order_by(LabellingJob.created_at.desc()).all()

    # Build responses with dataset names
    responses = []
    for job in jobs:
        dataset_name = job.dataset.name if job.dataset else None
        response = LabellingJobResponse(
            **job.__dict__,
            dataset_name=dataset_name
        )
        responses.append(response)

    return responses


@router.get("/labelling-jobs/{job_id}", response_model=LabellingJobResponse)
async def get_labelling_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific labelling job by ID"""
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    dataset_name = job.dataset.name if job.dataset else None
    response = LabellingJobResponse(
        **job.__dict__,
        dataset_name=dataset_name
    )
    return response


@router.patch("/labelling-jobs/{job_id}", response_model=LabellingJobResponse)
async def update_labelling_job(
    job_id: str,
    job_data: LabellingJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """Update a labelling job"""
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    # Update fields
    if job_data.name is not None:
        job.name = job_data.name
    if job_data.gcs_folder_path is not None:
        if not job_data.gcs_folder_path.startswith('gs://'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GCS folder path must start with gs://"
            )
        job.gcs_folder_path = job_data.gcs_folder_path
    if job_data.frequency_minutes is not None:
        job.frequency_minutes = job_data.frequency_minutes
        # Recalculate next run time
        if job.is_active:
            job.next_run_at = datetime.utcnow() + timedelta(minutes=job_data.frequency_minutes)
    if job_data.is_active is not None:
        job.is_active = job_data.is_active
        if job_data.is_active and not job.next_run_at:
            job.next_run_at = datetime.utcnow() + timedelta(minutes=job.frequency_minutes)
        elif not job_data.is_active:
            job.next_run_at = None

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    dataset_name = job.dataset.name if job.dataset else None
    response = LabellingJobResponse(
        **job.__dict__,
        dataset_name=dataset_name
    )
    return response


@router.delete("/labelling-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_labelling_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """Delete a labelling job and its associated dataset"""
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    # Delete associated dataset if it exists (cascade will handle images, results, etc.)
    if job.dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if dataset:
            db.delete(dataset)

    # Delete job (cascade will handle runs and results)
    db.delete(job)
    db.commit()

    logger.info(f"Deleted labelling job {job_id}")
    return None


@router.post("/labelling-jobs/{job_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_labelling_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """Manually trigger a labelling job execution"""
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    # Check if job is already running
    if job.status == 'running':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already running"
        )

    logger.info(f"Manual trigger for job {job_id}")

    # Execute in background thread
    run_job_in_thread(str(job_id), 'manual')

    return {"message": "Job execution started", "job_id": str(job_id)}


@router.get("/labelling-jobs/{job_id}/runs", response_model=List[LabellingJobRunResponse])
async def get_job_runs(
    job_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution history for a labelling job"""
    # Verify job access
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    # Get runs
    runs = db.query(LabellingJobRun).filter(
        LabellingJobRun.labelling_job_id == job_id
    ).order_by(LabellingJobRun.started_at.desc()).limit(limit).offset(offset).all()

    return runs


@router.get("/labelling-jobs/{job_id}/results", response_model=List[LabellingResultResponse])
async def get_job_results(
    job_id: str,
    run_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get labeling results for a job, optionally filtered by run"""
    # Verify job access
    job = db.query(LabellingJob).filter(
        LabellingJob.id == job_id,
        LabellingJob.created_by_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labelling job not found"
        )

    # Query results
    query = db.query(LabellingResult).filter(
        LabellingResult.labelling_job_id == job_id
    )

    if run_id:
        query = query.filter(LabellingResult.labelling_job_run_id == run_id)

    results = query.order_by(LabellingResult.created_at.desc()).limit(limit).offset(offset).all()

    return results
