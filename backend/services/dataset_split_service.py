from typing import List, Optional, Dict, Any
from uuid import UUID
import random
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, String

from models.dataset_split import DatasetSplit
from models.image import Image
from models.project import Dataset
from services.clustering_service import ClusteringService

logger = structlog.get_logger(__name__)

class DatasetSplitService:
    @staticmethod
    def create_split(
        db: Session,
        dataset_id: UUID,
        name: str,
        split_type: str,
        split_value: Optional[int],
        created_by_id: UUID,
        purpose: str = 'annotation',
        excluded_split_ids: Optional[List[UUID]] = None
    ) -> DatasetSplit:

        # 1. Get all image IDs for the dataset
        query = db.query(Image.id).filter(Image.dataset_id == dataset_id)

        # 2. Exclude images from previous splits if requested
        if excluded_split_ids:
            excluded_images = []
            for split_id in excluded_split_ids:
                split = db.query(DatasetSplit).filter(DatasetSplit.id == split_id).first()
                if split and split.image_ids:
                    excluded_images.extend(split.image_ids)

            if excluded_images:
                # Deduplicate
                excluded_images = list(set(excluded_images))
                query = query.filter(Image.id.notin_(excluded_images))

        available_image_ids = [str(r[0]) for r in query.all()]
        total_available = len(available_image_ids)

        selected_ids = []

        # 3. Apply Sampling Strategy
        if split_type == 'random_percent':
            if not split_value:
                raise ValueError("Split value (percent) is required for random_percent")
            count = int(total_available * (split_value / 100.0))
            selected_ids = random.sample(available_image_ids, min(count, total_available))

        elif split_type == 'random_count':
            if not split_value:
                raise ValueError("Split value (count) is required for random_count")
            selected_ids = random.sample(available_image_ids, min(split_value, total_available))

        elif split_type == 'k_means_centroid':
            # Diversity sampling using k-means clustering
            logger.info("using_kmeans_diversity_sampling", dataset_id=str(dataset_id), sample_size=split_value)

            # Use percentage if split_value is between 1-100, otherwise use count
            if split_value and split_value <= 100:
                count = int(total_available * (split_value / 100.0))
            else:
                count = split_value or int(total_available * 0.05)  # Default 5%

            # Use clustering service to select diverse samples
            try:
                selected_ids = ClusteringService.select_diverse_samples(
                    db=db,
                    dataset_id=dataset_id,
                    sample_size=count,
                    excluded_split_ids=excluded_split_ids
                )
            except ValueError as e:
                logger.error("kmeans_sampling_failed", error=str(e))
                raise ValueError(f"K-means sampling failed: {str(e)}. Ensure clustering has been performed on this dataset.")

        elif split_type == 'manual':
             # For manual, we expect the IDs to be passed in, but here we are "creating" the split logic.
             # Usually manual split creation comes with a list of IDs.
             # We'll assume for now this method is for *sampling*.
             # If manual, `image_ids` should be passed to a different method or we handle it here.
             pass

        # 4. Save
        # Serialize UUIDs to strings for JSON column
        excluded_splits_serialized = [str(sid) for sid in excluded_split_ids] if excluded_split_ids else None

        logger.info("creating_dataset_split",
                   dataset_id=str(dataset_id),
                   split_type=split_type,
                   purpose=purpose,
                   selected_count=len(selected_ids))

        new_split = DatasetSplit(
            dataset_id=dataset_id,
            name=name,
            image_ids=selected_ids,
            split_type=split_type,
            split_value=split_value,
            purpose=purpose,
            excluded_split_ids=excluded_splits_serialized,
            created_by_id=created_by_id
        )
        db.add(new_split)
        db.commit()
        db.refresh(new_split)

        logger.info("dataset_split_created", split_id=str(new_split.id))

        return new_split

    @staticmethod
    def get_split_images(db: Session, split_id: UUID) -> List[Image]:
        split = db.query(DatasetSplit).filter(DatasetSplit.id == split_id).first()
        if not split:
            return []

        return db.query(Image).filter(Image.id.in_(split.image_ids)).all()

    @staticmethod
    def create_unlabeled_pool(
        db: Session,
        dataset_id: UUID,
        created_by_id: UUID,
        name: str = "Unlabeled Pool"
    ) -> Optional[DatasetSplit]:
        """
        Create an unlabeled pool split containing all images not in any other split.

        This should be called after creating annotation and test sets to explicitly
        track the remaining unlabeled images.

        Args:
            db: Database session
            dataset_id: UUID of the dataset
            created_by_id: UUID of the user creating the split
            name: Name for the unlabeled pool split

        Returns:
            DatasetSplit for the unlabeled pool, or None if no unlabeled images remain
        """
        logger.info("creating_unlabeled_pool", dataset_id=str(dataset_id))

        # Get all existing splits for this dataset (excluding unlabeled_pool purpose)
        existing_splits = db.query(DatasetSplit).filter(
            DatasetSplit.dataset_id == dataset_id,
            DatasetSplit.purpose != 'unlabeled_pool'
        ).all()

        # Collect all image IDs already in splits
        used_image_ids = set()
        for split in existing_splits:
            if split.image_ids:
                used_image_ids.update(split.image_ids)

        logger.info("found_used_images", count=len(used_image_ids))

        # Get all image IDs in the dataset
        all_image_ids = [str(r[0]) for r in db.query(Image.id).filter(
            Image.dataset_id == dataset_id
        ).all()]

        # Calculate unlabeled images
        unlabeled_ids = [img_id for img_id in all_image_ids if img_id not in used_image_ids]

        logger.info("found_unlabeled_images", count=len(unlabeled_ids))

        if not unlabeled_ids:
            logger.info("no_unlabeled_images_remaining")
            return None

        # Check if unlabeled pool already exists and delete it (we'll recreate)
        existing_pool = db.query(DatasetSplit).filter(
            DatasetSplit.dataset_id == dataset_id,
            DatasetSplit.purpose == 'unlabeled_pool'
        ).first()

        if existing_pool:
            logger.info("deleting_existing_unlabeled_pool", split_id=str(existing_pool.id))
            db.delete(existing_pool)
            db.commit()

        # Create new unlabeled pool split
        unlabeled_pool = DatasetSplit(
            dataset_id=dataset_id,
            name=name,
            image_ids=unlabeled_ids,
            split_type='auto_remainder',
            split_value=len(unlabeled_ids),
            purpose='unlabeled_pool',
            excluded_split_ids=[str(s.id) for s in existing_splits],
            created_by_id=created_by_id
        )

        db.add(unlabeled_pool)
        db.commit()
        db.refresh(unlabeled_pool)

        logger.info("unlabeled_pool_created",
                   split_id=str(unlabeled_pool.id),
                   image_count=len(unlabeled_ids))

        return unlabeled_pool
