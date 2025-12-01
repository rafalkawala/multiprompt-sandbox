"""
Cleanup script to remove duplicate images from the database.

Keeps the most recent upload of each filename per dataset and removes older duplicates.
Also deletes the storage files for removed duplicates.

Usage:
    # Dry run (preview what will be deleted)
    python scripts/cleanup_duplicate_images.py --dry-run

    # Actually delete duplicates
    python scripts/cleanup_duplicate_images.py

    # Delete for specific dataset only
    python scripts/cleanup_duplicate_images.py --dataset-id <uuid>
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from sqlalchemy import func
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.image import Image
from services.storage_service import get_storage_provider
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_duplicates(dataset_id: str = None, dry_run: bool = True):
    """
    Remove duplicate images from database and storage.

    Args:
        dataset_id: Optional dataset ID to limit cleanup to specific dataset
        dry_run: If True, only preview changes without deleting
    """
    db: Session = SessionLocal()
    storage = get_storage_provider()

    try:
        # Find duplicates
        query = db.query(
            Image.dataset_id,
            Image.filename,
            func.count(Image.id).label('count')
        ).group_by(
            Image.dataset_id,
            Image.filename
        ).having(
            func.count(Image.id) > 1
        )

        if dataset_id:
            query = query.filter(Image.dataset_id == dataset_id)

        duplicates = query.all()

        logger.info(f"Found {len(duplicates)} duplicate filename groups")

        total_to_delete = 0
        deleted_count = 0

        for dataset_id, filename, count in duplicates:
            logger.info(f"Processing: {filename} in dataset {dataset_id} ({count} copies)")

            # Get all images with this filename in this dataset, ordered by upload date
            images = db.query(Image).filter(
                Image.dataset_id == dataset_id,
                Image.filename == filename
            ).order_by(Image.uploaded_at.desc()).all()

            # Keep the most recent, delete the rest
            to_keep = images[0]
            to_delete = images[1:]

            logger.info(f"  Keeping: {to_keep.id} (uploaded at {to_keep.uploaded_at})")

            for img in to_delete:
                total_to_delete += 1
                logger.info(f"  {'[DRY RUN] Would delete' if dry_run else 'Deleting'}: {img.id} (uploaded at {img.uploaded_at})")

                if not dry_run:
                    # Delete from storage
                    try:
                        await storage.delete(img.storage_path)
                        logger.info(f"    Deleted storage file: {img.storage_path}")
                    except Exception as e:
                        logger.warning(f"    Failed to delete storage file {img.storage_path}: {e}")

                    # Delete from database
                    db.delete(img)
                    deleted_count += 1

        if not dry_run:
            db.commit()
            logger.info(f"\nDeleted {deleted_count} duplicate images from database and storage")
        else:
            logger.info(f"\n[DRY RUN] Would delete {total_to_delete} duplicate images")
            logger.info("Run without --dry-run to actually delete")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Cleanup duplicate images')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without deleting')
    parser.add_argument('--dataset-id', type=str, help='Only cleanup specific dataset')

    args = parser.parse_args()

    # Run cleanup
    asyncio.run(cleanup_duplicates(
        dataset_id=args.dataset_id,
        dry_run=args.dry_run
    ))
