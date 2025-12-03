import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.labelling_job import LabellingJob, LabellingJobRun, LabellingResult
from models.project import Dataset, Project
from models.image import Image
from models.evaluation import ModelConfig
from services.gcs_scanner_service import GCSScannerService, GCSFileInfo
from services.storage_service import get_storage_provider
from services.cloud_tasks_service import get_cloud_tasks_service
from services.llm_service import get_llm_service
from core.config import settings

logger = logging.getLogger(__name__)


class LabellingJobService:
    """Service for executing labelling jobs"""

    def __init__(self):
        self.gcs_scanner = GCSScannerService()
        self.storage = get_storage_provider()

    async def run_job(
        self,
        job_id: str,
        db: Session,
        trigger_type: str = 'manual'
    ) -> LabellingJobRun:
        """
        Execute a labelling job.

        Args:
            job_id: UUID of the job to run
            db: Database session
            trigger_type: 'manual' or 'scheduled'

        Returns:
            LabellingJobRun record
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting labelling job {job_id} (trigger: {trigger_type})")

        # Get job
        job = db.query(LabellingJob).filter(LabellingJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Create run record
        run = LabellingJobRun(
            labelling_job_id=job_id,
            trigger_type=trigger_type,
            status='running',
            started_at=start_time
        )
        db.add(run)

        # Update job status
        job.status = 'running'
        job.last_run_at = start_time
        db.commit()

        try:
            # Step 1: Ensure dataset exists
            if not job.dataset_id:
                logger.info(f"Creating dedicated dataset for job {job.name}")
                dataset = await self._create_dataset(job, db)
                job.dataset_id = dataset.id
                db.commit()
            else:
                dataset = job.dataset

            # Step 2: Scan GCS folder for new files
            logger.info(f"Scanning GCS folder: {job.gcs_folder_path}")
            files = self.gcs_scanner.scan_folder(
                job.gcs_folder_path,
                last_processed_timestamp=job.last_processed_timestamp
            )
            run.images_discovered = len(files)
            db.commit()

            if not files:
                logger.info(f"No new files found for job {job_id}")
                run.status = 'completed'
                run.completed_at = datetime.utcnow()
                run.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
                db.commit()
                return run

            logger.info(f"Found {len(files)} new files to process")

            # Step 3: Ingest images
            logger.info(f"Starting ingestion of {len(files)} discovered files...")
            images = await self._ingest_images(job, dataset, files, run, db)
            run.images_ingested = len(images)
            db.commit()

            logger.info(f"Ingestion result: {len(images)} images ingested, {run.images_failed} failed")

            if not images:
                logger.warning(f"No images were successfully ingested for job {job_id}. Check logs above for errors.")
                run.status = 'completed'
                run.completed_at = datetime.utcnow()
                run.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
                db.commit()
                return run

            # Step 4: Skip waiting for thumbnails - labelling works on full images
            # Thumbnails are generated asynchronously by Cloud Tasks for UI preview only
            logger.info(f"Thumbnail generation enqueued (async). Proceeding with labelling...")

            # Step 5: Generate labels
            logger.info(f"Generating labels for {len(images)} images...")
            results = await self._generate_labels(job, run, images, db)
            run.images_labeled = len([r for r in results if not r.error])
            run.images_failed = len([r for r in results if r.error])
            db.commit()

            # Step 6: Update job statistics
            job.total_runs += 1
            job.total_images_processed += run.images_ingested
            job.total_images_labeled += run.images_labeled
            job.total_errors += run.images_failed

            # Update last processed timestamp to the latest file creation time
            if files:
                job.last_processed_timestamp = max(f.time_created for f in files)

            job.status = 'idle'
            db.commit()

            # Mark run as completed
            run.status = 'completed'
            run.completed_at = datetime.utcnow()
            run.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
            db.commit()

            logger.info(f"✓ Job {job_id} completed: {run.images_labeled} labeled, {run.images_failed} failed")
            return run

        except Exception as e:
            logger.error(f"✗ Job {job_id} failed: {str(e)}", exc_info=True)

            # Rollback any pending transaction before updating
            db.rollback()

            # Reload objects from database
            db.expire_all()

            # Update run status
            run.status = 'failed'
            run.error_message = str(e)
            run.error_details = {'traceback': str(e)}
            run.completed_at = datetime.utcnow()
            run.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())

            # Update job status
            job.status = 'error'
            job.total_errors += 1

            db.commit()
            raise

    async def _create_dataset(self, job: LabellingJob, db: Session) -> Dataset:
        """Create a dedicated dataset for the job"""
        dataset = Dataset(
            name=f"Job Output: {job.name}",
            project_id=job.project_id,
            created_by_id=job.created_by_id,
            processing_status='ready'
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        logger.info(f"Created dataset {dataset.id}: {dataset.name}")
        return dataset

    async def _ingest_images(
        self,
        job: LabellingJob,
        dataset: Dataset,
        files: List[GCSFileInfo],
        run: LabellingJobRun,
        db: Session
    ) -> List[Image]:
        """
        Ingest images from GCS into the dataset.
        Copies files, creates Image records, handles duplicates, and enqueues thumbnail generation.
        """
        ingested_images = []

        # Get existing filenames in dataset to detect duplicates
        existing_filenames = {
            img.filename for img in db.query(Image.filename).filter(
                Image.dataset_id == dataset.id
            ).all()
        }

        for file_info in files:
            try:
                logger.info(f"Starting ingestion of {file_info.filename} from {file_info.full_path}")

                # Handle duplicate filenames by appending UUID
                filename = file_info.filename
                if filename in existing_filenames:
                    base, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                    filename = f"{base}_{str(uuid.uuid4())[:8]}.{ext}"
                    logger.info(f"Renamed duplicate {file_info.filename} to {filename}")

                # Destination path in project/dataset structure
                destination_path = f"projects/{job.project_id}/datasets/{dataset.id}/{filename}"
                logger.info(f"Destination path: {destination_path}")

                # Copy blob from source to destination
                if settings.STORAGE_TYPE == 'gcs':
                    # Use GCS copy
                    logger.info(f"Using GCS storage, copying from {file_info.full_path}")
                    bucket_name = self.gcs_scanner.client.bucket(settings.GCS_BUCKET_NAME).name
                    logger.info(f"Destination bucket: {bucket_name}")

                    destination_full_path, size = self.gcs_scanner.copy_blob(
                        file_info.full_path,
                        bucket_name,
                        destination_path
                    )
                    logger.info(f"✓ Copied to {destination_full_path}, size: {size} bytes")
                else:
                    # For local storage, download and re-upload
                    logger.info(f"Using local storage")
                    file_data = await self.storage.download(file_info.blob_name)
                    destination_path, size = await self.storage.upload(file_data, destination_path)

                # Create Image record
                image = Image(
                    dataset_id=dataset.id,
                    filename=filename,
                    storage_path=destination_path,
                    file_size=size,
                    uploaded_by_id=job.created_by_id,  # Set to job creator
                    processing_status='pending'  # Will be processed for thumbnails
                )
                db.add(image)
                db.flush()  # Get image ID

                ingested_images.append(image)
                existing_filenames.add(filename)

                logger.info(f"✓ Successfully ingested image {image.id}: {filename} ({size} bytes)")

            except Exception as e:
                logger.error(f"✗ Failed to ingest {file_info.filename}: {str(e)}", exc_info=True)
                run.images_failed += 1

        db.commit()

        # Log ingestion summary
        logger.info(f"Ingestion complete: {len(ingested_images)} succeeded, {run.images_failed} failed out of {len(files)} total")

        # Enqueue Cloud Task for thumbnail generation if images were ingested
        if ingested_images and settings.USE_CLOUD_TASKS:
            try:
                cloud_tasks = get_cloud_tasks_service()
                task_name = cloud_tasks.enqueue_dataset_processing(
                    str(job.project_id),
                    str(dataset.id)
                )
                logger.info(f"✓ Enqueued thumbnail generation task: {task_name}")
            except Exception as e:
                logger.error(f"Failed to enqueue thumbnail task: {str(e)}")

        return ingested_images

    async def _wait_for_thumbnails(self, images: List[Image], db: Session, timeout: int = 600):
        """
        Poll until all thumbnails are generated or timeout.

        Args:
            images: List of images to wait for
            db: Database session
            timeout: Maximum time to wait in seconds (default: 10 minutes)
        """
        if not settings.USE_CLOUD_TASKS:
            # In local mode, thumbnails are generated synchronously
            return

        start_time = datetime.utcnow()
        image_ids = [img.id for img in images]

        while True:
            # Check if all images are processed
            pending_count = db.query(func.count(Image.id)).filter(
                Image.id.in_(image_ids),
                Image.processing_status == 'pending'
            ).scalar()

            if pending_count == 0:
                logger.info("✓ All thumbnails generated successfully")
                break

            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                logger.warning(f"Thumbnail generation timeout after {timeout}s. {pending_count} images still pending.")
                break

            # Wait before next check
            await asyncio.sleep(5)

            # Refresh session
            db.expire_all()

    async def _generate_labels(
        self,
        job: LabellingJob,
        run: LabellingJobRun,
        images: List[Image],
        db: Session
    ) -> List[LabellingResult]:
        """
        Generate labels for images using LLM.

        Args:
            job: The labelling job
            run: The current job run
            images: List of images to label
            db: Database session

        Returns:
            List of LabellingResult records
        """
        # Get model config
        model_config = job.model_config

        # Preload all images into cache
        logger.info(f"Preloading {len(images)} images...")
        image_cache = await self._preload_images(images)

        if len(image_cache) == 0:
            logger.error("Failed to load any images for labeling")
            return []

        # Get concurrency limit from model config
        concurrency = getattr(model_config, 'concurrency', 3)
        semaphore = asyncio.Semaphore(concurrency)

        results = []

        # Process images in parallel with concurrency limit
        async def process_image(image: Image):
            async with semaphore:
                try:
                    # Get cached image data
                    cached_data = image_cache.get(image.id)
                    if not cached_data:
                        raise Exception(f"Image {image.id} not found in cache")

                    image_data, mime_type = cached_data

                    # Call LLM Service
                    llm_service = get_llm_service()
                    start = datetime.utcnow()
                    response_text, latency = await llm_service.generate_content(
                        provider_name=model_config.provider,
                        api_key=model_config.api_key,
                        model_name=model_config.model_name,
                        image_data=image_data,
                        mime_type=mime_type,
                        prompt=job.question_text,
                        system_message=job.system_message,
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens
                    )

                    # Parse answer (reuse evaluation logic)
                    parsed_answer = self._parse_answer(response_text, job.project.question_type)

                    # Create result record
                    result = LabellingResult(
                        labelling_job_id=job.id,
                        labelling_job_run_id=run.id,
                        image_id=image.id,
                        model_response=response_text,
                        parsed_answer=parsed_answer,
                        latency_ms=latency,
                        gcs_source_path=image.storage_path
                    )
                    db.add(result)
                    results.append(result)

                    logger.info(f"✓ Labeled image {image.id}: {parsed_answer}")

                except Exception as e:
                    logger.error(f"✗ Failed to label image {image.id}: {str(e)}")

                    # Create error result
                    result = LabellingResult(
                        labelling_job_id=job.id,
                        labelling_job_run_id=run.id,
                        image_id=image.id,
                        model_response="",
                        parsed_answer={},
                        error=str(e),
                        gcs_source_path=image.storage_path
                    )
                    db.add(result)
                    results.append(result)

        # Process all images in parallel
        await asyncio.gather(*[process_image(img) for img in images])

        db.commit()
        return results

    async def _preload_images(self, images: List[Image]) -> Dict[str, Tuple[str, str]]:
        """
        Preload all images into memory cache.

        Returns:
            Dict mapping image_id to (base64_data, mime_type)
        """
        import base64

        cache = {}

        async def load_image(image: Image):
            try:
                # Download from storage
                file_data = await self.storage.download(image.storage_path)

                # Convert to base64
                image_data = base64.b64encode(file_data).decode('utf-8')

                # Determine MIME type from extension
                ext = image.filename.split('.')[-1].lower()
                mime_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp',
                    'bmp': 'image/bmp'
                }
                mime_type = mime_map.get(ext, 'image/jpeg')

                cache[image.id] = (image_data, mime_type)
                logger.debug(f"Preloaded image {image.id}")

            except Exception as e:
                logger.error(f"Failed to preload image {image.id}: {str(e)}")

        # Load all images in parallel
        await asyncio.gather(*[load_image(img) for img in images])

        logger.info(f"Preloaded {len(cache)}/{len(images)} images")
        return cache

    def _parse_answer(self, response: str, question_type: str) -> dict:
        """Parse model response based on question type (copied from evaluations.py)"""
        response_lower = response.lower().strip()

        if question_type == 'binary':
            if any(word in response_lower for word in ['yes', 'true', '1']):
                return {'value': True}
            elif any(word in response_lower for word in ['no', 'false', '0']):
                return {'value': False}
            return {'value': None, 'raw': response}

        elif question_type == 'count':
            import re
            numbers = re.findall(r'\d+', response)
            if numbers:
                return {'value': int(numbers[0])}
            return {'value': None, 'raw': response}

        elif question_type == 'multiple_choice':
            return {'value': response.strip()}

        else:  # text
            return {'value': response.strip()}


# Singleton instance
_labelling_job_service = None


def get_labelling_job_service() -> LabellingJobService:
    """Get the LabellingJobService singleton instance"""
    global _labelling_job_service
    if _labelling_job_service is None:
        _labelling_job_service = LabellingJobService()
    return _labelling_job_service
