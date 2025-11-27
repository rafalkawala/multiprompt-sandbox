"""
Internal task endpoints for Cloud Tasks to call.
These endpoints are protected and should only be called by Cloud Tasks.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from core.database import SessionLocal
from services.image_processing_service import ImageProcessingService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
