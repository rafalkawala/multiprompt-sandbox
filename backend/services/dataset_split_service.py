from typing import List, Optional, Dict, Any
from uuid import UUID
import random
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, String

from models.dataset_split import DatasetSplit
from models.image import Image
from models.project import Dataset

class DatasetSplitService:
    @staticmethod
    def create_split(
        db: Session,
        dataset_id: UUID,
        name: str,
        split_type: str,
        split_value: Optional[int],
        created_by_id: UUID,
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

        elif split_type == 'manual':
             # For manual, we expect the IDs to be passed in, but here we are "creating" the split logic.
             # Usually manual split creation comes with a list of IDs.
             # We'll assume for now this method is for *sampling*.
             # If manual, `image_ids` should be passed to a different method or we handle it here.
             pass

        # 4. Save
        # Serialize UUIDs to strings for JSON column
        excluded_splits_serialized = [str(sid) for sid in excluded_split_ids] if excluded_split_ids else None

        new_split = DatasetSplit(
            dataset_id=dataset_id,
            name=name,
            image_ids=selected_ids,
            split_type=split_type,
            split_value=split_value,
            excluded_split_ids=excluded_splits_serialized,
            created_by_id=created_by_id
        )
        db.add(new_split)
        db.commit()
        db.refresh(new_split)
        return new_split

    @staticmethod
    def get_split_images(db: Session, split_id: UUID) -> List[Image]:
        split = db.query(DatasetSplit).filter(DatasetSplit.id == split_id).first()
        if not split:
            return []

        return db.query(Image).filter(Image.id.in_(split.image_ids)).all()
