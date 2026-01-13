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
        logger.info("starting_image_processing", dataset_id=dataset_id)

        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.error("dataset_not_found", dataset_id=dataset_id)
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

        logger.info("found_images_to_process", image_count=len(images), dataset_id=dataset_id)

        if not images:
            dataset.processing_status = "completed"
            dataset.processing_completed_at = datetime.utcnow()
            db.commit()
            return

        # Process with concurrency limit
        semaphore = asyncio.Semaphore(5)  # 5 concurrent processing tasks

        # Get preferred embedding model from service (which loads from config)
        # In the future, this could be passed as an argument or read from dataset settings
        embedding_models = self.embedding_service.get_available_models()
        embedding_model_name = None
        embedding_provider_name = None
        if embedding_models:
             # Just picking the first available one for now as a default
             # This logic could be improved to prefer a specific one or check config
             embedding_model_name = embedding_models[0].get("model_name")
             embedding_provider_name = embedding_models[0].get("provider")

        logger.info("using_embedding_model", model_name=embedding_model_name or 'default', provider=embedding_provider_name or 'auto')

        async def process_single_image(image: Image):
            """Process a single image: download, generate thumbnail, generate embedding, update DB"""
            async with semaphore:
                try:
                    logger.info("processing_image", image_id=image.id, filename=image.filename)

                    # Update image status
                    image.processing_status = "processing"
                    db.commit()

                    # Download image from storage
                    file_data = await self.storage.download(image.storage_path)
                    logger.info("downloaded_image", image_id=image.id, size_bytes=len(file_data))

                    # Generate thumbnail in thread pool (CPU-bound operation)
                    loop = asyncio.get_event_loop()

                    thumbnail_future = loop.run_in_executor(
                        self.executor,
                        generate_thumbnail,
                        file_data
                    )

                    # Generate embedding (I/O bound API call)
                    async def generate_emb():
                        try:
                            # We allow model selection here via the variable above
                            logger.info("generating_embedding", image_id=image.id, model_name=embedding_model_name)
                            response = await self.embedding_service.generate_embeddings(
                                image_bytes=file_data,
                                model_name=embedding_model_name,
                                provider_name=embedding_provider_name
                            )
                            if response and response.image_embedding:
                                return response.image_embedding
                            return None
                        except Exception as emb_err:
                            logger.error("embedding_generation_failed", image_id=image.id, error=str(emb_err))
                            return None # Soft failure for embeddings

                    thumbnail_bytes, embedding_vector = await asyncio.gather(
                        thumbnail_future,
                        generate_emb()
                    )

                    logger.info("thumbnail_generated", image_id=image.id, size_bytes=len(thumbnail_bytes))
                    if embedding_vector:
                         logger.info("embedding_generated", image_id=image.id, dimension=len(embedding_vector))

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

                    logger.info("image_processed_successfully", image_id=image.id)
                    return True

                except Exception as e:
                    logger.error("image_processing_failed", image_id=image.id, error=str(e), exc_info=True)

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

        logger.info("processing_complete", dataset_id=dataset_id, success_count=success_count, failure_count=failure_count)

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

        logger.info("dataset_processing_finished", dataset_id=dataset_id, status=dataset.processing_status)
