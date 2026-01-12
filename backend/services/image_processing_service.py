import asyncio
import structlog
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy.orm import Session
from models.image import Image
from models.project import Dataset
from core.image_utils import generate_thumbnail
from services.storage_service import get_storage_provider
from services.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)


class ImageProcessingService:
    """Service for processing images in the background (thumbnails, validation, etc.)"""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.storage = get_storage_provider()
        self.embedding_service = get_embedding_service()

    async def process_dataset_images(self, dataset_id: str, db: Session):
        """
        Process all pending images in a dataset.
        Generates thumbnails, performs validation, and generates embeddings.

        Args:
            dataset_id: UUID of the dataset to process
            db: Database session
        """
        logger.info(f"Starting image processing for dataset {dataset_id}")

        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.error(f"Dataset {dataset_id} not found")
            return

        # Update dataset status
        dataset.processing_status = "processing"
        dataset.processing_started_at = datetime.utcnow()
        db.commit()

        # Get all pending images
        images = db.query(Image).filter(
            Image.dataset_id == dataset_id,
            Image.processing_status == "pending"
        ).all()

        logger.info(f"Found {len(images)} images to process in dataset {dataset_id}")

        if not images:
            dataset.processing_status = "completed"
            dataset.processing_completed_at = datetime.utcnow()
            db.commit()
            return

        # Process with concurrency limit
        semaphore = asyncio.Semaphore(5)  # 5 concurrent processing tasks

        async def process_single_image(image: Image):
            """Process a single image: download, generate thumbnail, generate embedding, update DB"""
            async with semaphore:
                try:
                    logger.info(f"Processing image {image.id}: {image.filename}")

                    # Update image status
                    image.processing_status = "processing"
                    db.commit()

                    # Download image from storage
                    file_data = await self.storage.download(image.storage_path)
                    logger.info(f"Downloaded image {image.id} ({len(file_data)} bytes)")

                    # Generate thumbnail in thread pool (CPU-bound operation)
                    loop = asyncio.get_event_loop()

                    thumbnail_future = loop.run_in_executor(
                        self.executor,
                        generate_thumbnail,
                        file_data
                    )

                    # Generate embedding (I/O bound API call)
                    # We run this concurrently with thumbnail generation if possible,
                    # but since thumbnail is fast, we can just await it or gather.
                    # Since generate_embeddings is async, we can await it directly.
                    # To parallelize CPU task (thumbnail) and IO task (embedding), we use gather.

                    async def generate_emb():
                        try:
                            logger.info(f"Generating embedding for image {image.id}")
                            response = await self.embedding_service.generate_embeddings(
                                image_bytes=file_data
                            )
                            # Convert to list/json compatible format if it's not already
                            # EmbeddingResponse.image_embedding is likely a list of floats
                            if response and response.image_embedding:
                                return response.image_embedding
                            return None
                        except Exception as emb_err:
                            logger.error(f"Embedding generation failed for image {image.id}: {emb_err}")
                            return None # Soft failure for embeddings

                    thumbnail_bytes, embedding_vector = await asyncio.gather(
                        thumbnail_future,
                        generate_emb()
                    )

                    logger.info(f"Generated thumbnail for image {image.id} ({len(thumbnail_bytes)} bytes)")
                    if embedding_vector:
                         logger.info(f"Generated embedding for image {image.id} (dim: {len(embedding_vector)})")

                    # Update database
                    image.thumbnail_data = thumbnail_bytes
                    if embedding_vector:
                        image.embedding = embedding_vector

                    image.processing_status = "completed"
                    image.processing_error = None
                    db.commit()

                    # Update dataset progress
                    dataset.processed_files += 1
                    db.commit()

                    logger.info(f"Successfully processed image {image.id}")
                    return True

                except Exception as e:
                    logger.error(f"Failed to process image {image.id}: {str(e)}", exc_info=True)

                    # Mark image as failed
                    image.processing_status = "failed"
                    image.processing_error = str(e)
                    db.commit()

                    # Update dataset failed count
                    dataset.failed_files += 1
                    db.commit()

                    return False

        # Process all images in parallel
        results = await asyncio.gather(
            *[process_single_image(img) for img in images],
            return_exceptions=True
        )

        # Count successes and failures
        success_count = sum(1 for r in results if r is True)
        failure_count = sum(1 for r in results if r is False or isinstance(r, Exception))

        logger.info(f"Processing complete for dataset {dataset_id}: {success_count} succeeded, {failure_count} failed")

        # Update dataset final status
        if dataset.failed_files == 0:
            dataset.processing_status = "completed"
        else:
            dataset.processing_status = "failed"
            # Store error summary
            error_messages = [
                f"{img.filename}: {img.processing_error}"
                for img in images
                if img.processing_status == "failed" and img.processing_error
            ]
            if error_messages:
                dataset.processing_errors = error_messages[:10]  # Limit to first 10 errors

        dataset.processing_completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Dataset {dataset_id} processing finished with status: {dataset.processing_status}")
