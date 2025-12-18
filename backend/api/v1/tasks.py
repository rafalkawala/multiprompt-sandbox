"""
Internal task endpoints for Cloud Tasks to call.
These endpoints are protected and should only be called by Cloud Tasks.
"""
import structlog
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from api.deps import get_db
from services.image_processing_service import ImageProcessingService
from services.labelling_job_service import get_labelling_job_service
from services.cloud_tasks_service import get_cloud_tasks_service
from models.labelling_job import LabellingJob

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/internal/tasks/process-dataset/{dataset_id}")
async def process_dataset_task(
    dataset_id: str,
    db: Session = Depends(get_db),
    x_cloudtasks_taskname: str | None = Header(None)
):
    """
    Background task endpoint - processes images in a dataset.
    Called by Cloud Tasks to generate thumbnails and validate images.

    This endpoint is protected and should only be called by Cloud Tasks.

    Args:
        dataset_id: UUID of the dataset to process
        x_cloudtasks_taskname: Header set by Cloud Tasks (for verification)

    Returns:
        Processing status
    """
    # Security: Verify request is from Cloud Tasks
    # Cloud Tasks automatically adds X-CloudTasks-TaskName header
    if not x_cloudtasks_taskname:
        logger.warning(f"Unauthorized access attempt to process-dataset endpoint")
        raise HTTPException(status_code=403, detail="Unauthorized - must be called by Cloud Tasks")

    logger.info(f"Processing dataset {dataset_id} (task: {x_cloudtasks_taskname})")

    try:
        # Create service and process dataset
        service = ImageProcessingService()
        await service.process_dataset_images(dataset_id, db)

        logger.info(f"Dataset {dataset_id} processing completed successfully")
        return {
            "status": "completed",
            "dataset_id": dataset_id,
            "task_name": x_cloudtasks_taskname
        }

    except Exception as e:
        logger.error(f"Error processing dataset {dataset_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/internal/tasks/run-labelling-job/{job_id}")
async def run_labelling_job_task(
    job_id: str,
    db: Session = Depends(get_db),
    x_cloudtasks_taskname: str | None = Header(None)
):
    """
    Background task endpoint - runs a labelling job.
    Called by Cloud Tasks to execute labelling job workflow.

    Args:
        job_id: UUID of the labelling job to run
        x_cloudtasks_taskname: Header set by Cloud Tasks (for verification)

    Returns:
        Execution status
    """
    # Security: Verify request is from Cloud Tasks
    if not x_cloudtasks_taskname:
        logger.warning(f"Unauthorized access attempt to run-labelling-job endpoint")
        raise HTTPException(status_code=403, detail="Unauthorized - must be called by Cloud Tasks")

    logger.info(f"Running labelling job {job_id} (task: {x_cloudtasks_taskname})")

    try:
        # Get service and run job
        service = get_labelling_job_service()
        run = await service.run_job(job_id, db, trigger_type='scheduled')

        logger.info(f"Labelling job {job_id} completed successfully")
        return {
            "status": "completed",
            "job_id": job_id,
            "run_id": str(run.id),
            "images_labeled": run.images_labeled,
            "images_failed": run.images_failed,
            "task_name": x_cloudtasks_taskname
        }

    except Exception as e:
        logger.error(f"Error running labelling job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@router.post("/internal/tasks/check-scheduled-jobs")
async def check_scheduled_jobs_task(
    db: Session = Depends(get_db),
    x_cloudscheduler: str | None = Header(None)
):
    """
    Scheduler endpoint - checks for labelling jobs that need to run.
    Called by Cloud Scheduler every 15 minutes to trigger due jobs.

    This endpoint:
    1. Queries active jobs where next_run_at <= now()
    2. Enqueues Cloud Tasks for each due job
    3. Updates next_run_at for each job

    Args:
        x_cloudscheduler: Header set by Cloud Scheduler (for verification)

    Returns:
        Summary of jobs triggered
    """
    # Security: Verify request is from Cloud Scheduler
    # Cloud Scheduler adds X-CloudScheduler header
    if not x_cloudscheduler:
        logger.warning(f"Unauthorized access attempt to check-scheduled-jobs endpoint")
        raise HTTPException(status_code=403, detail="Unauthorized - must be called by Cloud Scheduler")

    logger.info(f"Checking scheduled labelling jobs (scheduler: {x_cloudscheduler})")

    try:
        now = datetime.utcnow()

        # Query active jobs that are due
        due_jobs = db.query(LabellingJob).filter(
            LabellingJob.is_active == True,
            LabellingJob.next_run_at <= now
        ).all()

        logger.info(f"Found {len(due_jobs)} labelling jobs due for execution")

        triggered_jobs = []
        failed_jobs = []

        # Enqueue tasks for each due job
        cloud_tasks = get_cloud_tasks_service()

        for job in due_jobs:
            try:
                # Enqueue Cloud Task
                task_name = cloud_tasks.enqueue_labelling_job_task(str(job.id))

                # Update next run time
                job.next_run_at = now + timedelta(minutes=job.frequency_minutes)
                db.commit()

                triggered_jobs.append({
                    "job_id": str(job.id),
                    "job_name": job.name,
                    "task_name": task_name
                })

                logger.info(f"✓ Enqueued job {job.id}: {job.name}")

            except Exception as e:
                logger.error(f"✗ Failed to enqueue job {job.id}: {str(e)}")
                failed_jobs.append({
                    "job_id": str(job.id),
                    "job_name": job.name,
                    "error": str(e)
                })

        return {
            "status": "completed",
            "triggered_count": len(triggered_jobs),
            "failed_count": len(failed_jobs),
            "triggered_jobs": triggered_jobs,
            "failed_jobs": failed_jobs
        }

    except Exception as e:
        logger.error(f"Error checking scheduled jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scheduler check failed: {str(e)}")
