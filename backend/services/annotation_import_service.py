"""
Service for importing and validating CSV annotations with async support
"""
import pandas as pd
from typing import Optional, Dict, List, Any
from io import BytesIO
import os
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
import structlog
import uuid

from models.project import Project, Dataset
from models.image import Image, Annotation
from models.import_job import AnnotationImportJob, ImportJobStatus
from core.database import SessionLocal

logger = structlog.get_logger(__name__)


class AnnotationImportService:
    """Service for importing and validating CSV annotations"""

    # Binary label normalization sets (case insensitive)
    BINARY_TRUE_VALUES = {'yes', 'y', 'true', 't', '1', '1.0'}
    BINARY_FALSE_VALUES = {'no', 'n', 'false', 'f', '0', '0.0'}
    
    BATCH_SIZE = 100
    MAX_STORED_ERRORS = 1000

    def __init__(self, project: Project, dataset: Dataset, db_session: Session):
        self.project = project
        self.dataset = dataset
        self.db = db_session

    def create_import_job(self, user_id: str, temp_file_path: str) -> AnnotationImportJob:
        """Create a new import job record"""
        job = AnnotationImportJob(
            dataset_id=self.dataset.id,
            created_by_id=user_id,
            status=ImportJobStatus.PENDING,
            temp_file_path=temp_file_path
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    async def process_import_job(self, job_id: str):
        """
        Background task to process the import job.
        Handles chunked reading, validation, and bulk updates.
        """
        logger.info(f"Starting import job {job_id}")
        
        # New DB session for the background task
        db = SessionLocal()
        
        try:
            job = db.query(AnnotationImportJob).filter(AnnotationImportJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            job.status = ImportJobStatus.PROCESSING
            db.commit()

            if not os.path.exists(job.temp_file_path):
                raise FileNotFoundError(f"Temp file not found: {job.temp_file_path}")

            # 1. Count total rows first
            try:
                with open(job.temp_file_path, 'r', encoding='utf-8') as f:
                    job.total_rows = sum(1 for row in f) - 1 # minus header
                    if job.total_rows < 0: job.total_rows = 0
            except Exception:
                job.total_rows = 0 # unknown
            
            db.commit()

            # 2. Process in chunks
            # Re-init service with new session
            # We need to re-fetch project/dataset as well since session is new
            dataset = db.query(Dataset).get(job.dataset_id)
            project = db.query(Project).get(dataset.project_id)
            
            # Helper to access logic
            service = AnnotationImportService(project, dataset, db)
            
            chunk_iterator = pd.read_csv(job.temp_file_path, chunksize=self.BATCH_SIZE)
            
            processed_count = 0
            
            for chunk in chunk_iterator:
                # Process this chunk
                start_row = processed_count + 2 # +1 header +1 1-based
                
                chunk_results = service.process_chunk(chunk, start_row, str(job.created_by_id))
                
                # Update job stats
                job.processed_rows += len(chunk)
                job.created_count += chunk_results['created']
                job.updated_count += chunk_results['updated']
                job.skipped_count += chunk_results['skipped']
                job.error_count += len(chunk_results['errors'])
                
                # Append errors (limit to prevent massive JSON)
                if chunk_results['errors']:
                    current_errors = list(job.errors) if job.errors else []
                    if len(current_errors) < self.MAX_STORED_ERRORS:
                        current_errors.extend(chunk_results['errors'])
                        job.errors = current_errors
                
                processed_count += len(chunk)
                db.commit() # Commit batch progress
                
                # Allow other tasks to run
                await asyncio.sleep(0.01)

            # Done
            job.status = ImportJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            # Cleanup file
            # We keep the file for debugging if needed, or delete on success.
            # Review Recommendation: Keep temp files for 24-48 hours. 
            # For now, we will delete on success to save space, but log failure on deletion.
            # If we want to implement delayed cleanup, we need a cron job.
            if os.path.exists(job.temp_file_path):
                try:
                    os.remove(job.temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {job.temp_file_path}: {e}")

        except Exception as e:
            logger.error(f"Import job {job_id} failed: {e}", exc_info=True)
            if job:
                job.status = ImportJobStatus.FAILED
                # Append system error to errors list
                error_msg = {"row": 0, "error": f"System error: {str(e)}"}
                current_errors = list(job.errors) if job.errors else []
                current_errors.append(error_msg)
                job.errors = current_errors
                db.commit()
        finally:
            db.close()

    def process_chunk(self, df: pd.DataFrame, start_row_num: int, user_id: str) -> Dict[str, Any]:
        """
        Process a chunk of rows: validate and apply changes.
        Optimized for bulk operations where possible.
        """
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        # 0. Validate Columns
        required_cols = {'image_filename', 'annotation_value'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            stats['errors'].append({'row': 0, 'error': f"Missing columns: {', '.join(missing_cols)}"})
            return stats

        # 1. Bulk fetch images to minimize queries
        # Get all filenames in this chunk
        filenames = df['image_filename'].dropna().astype(str).unique().tolist()
        
        # Fetch all images with these filenames in this dataset
        # Eager load annotations to prevent N+1 queries
        images_query = self.db.query(Image).options(
            joinedload(Image.annotation)
        ).filter(
            Image.dataset_id == self.dataset.id,
            Image.filename.in_(filenames)
        ).all()
        
        image_map = {} # filename -> list of images (sorted by ID)
        for img in images_query:
            if img.filename not in image_map:
                image_map[img.filename] = []
            image_map[img.filename].append(img)
            
        # Sort lists by ID to ensure deterministic matching for duplicates
        for fname in image_map:
            image_map[fname].sort(key=lambda x: x.id)

        # 2. Iterate rows and validate/prepare
        # Use enumerate to correctly calculate row number in loop
        for idx, (_, row) in enumerate(df.iterrows()):
            row_num = start_row_num + idx
            
            # Find image
            filename = str(row.get('image_filename', '')).strip()
            
            # Duplicate Handling Policy:
            # If multiple images exist with the same filename in the DB, 
            # we match the FIRST one (sorted by ID) and update/annotate it.
            # We do not currently support annotating specific duplicate instances via CSV 
            # (unless we added ID support back, but filename is primary key in CSV).
            
            target_image = None
            if filename in image_map and image_map[filename]:
                target_image = image_map[filename][0]
            else:
                stats['errors'].append({'row': row_num, 'error': f"Image not found: {filename}"})
                continue
            
            # Check value
            raw_value = row.get('annotation_value')
            if pd.isna(raw_value) or raw_value == '':
                stats['skipped'] += 1
                continue

            try:
                normalized = self.validate_value(
                    raw_value, 
                    self.project.question_type, 
                    self.project.question_options
                )
                
                if target_image.annotation:
                    # Update
                    target_image.annotation.answer_value = {'value': normalized}
                    target_image.annotation.annotator_id = user_id
                    stats['updated'] += 1
                else:
                    # Create
                    ann = Annotation(
                        image_id=target_image.id,
                        answer_value={'value': normalized},
                        annotator_id=user_id
                    )
                    self.db.add(ann)
                    stats['created'] += 1
                    
                    # Update relationship manually so next row in this chunk knows it exists
                    # (In case multiple rows refer to same image - last one wins)
                    target_image.annotation = ann

            except ValueError as e:
                stats['errors'].append({'row': row_num, 'error': str(e)})

        return stats

    def normalize_binary(self, value: Any) -> Optional[bool]:
        """
        Normalize binary value to True/False/None.
        """
        if pd.isna(value) or value == '' or value is None:
            return None

        value_lower = str(value).strip().lower()

        if value_lower in self.BINARY_TRUE_VALUES:
            return True
        elif value_lower in self.BINARY_FALSE_VALUES:
            return False
        else:
            raise ValueError(
                f"Invalid binary value: '{value}'. "
                f"Accepted: yes/no, y/n, true/false, t/f, 1/0"
            )

    def validate_value(self, value: Any, question_type: str, question_options: Optional[List[str]] = None) -> Any:
        """
        Validate and normalize annotation value.
        """
        if pd.isna(value) or value == '' or value is None:
            return None

        if question_type == 'binary':
            return self.normalize_binary(value)

        elif question_type == 'multiple_choice':
            if not question_options:
                raise ValueError("No question options defined for multiple choice question")

            value_str = str(value).strip()
            # Try exact match first
            if value_str in question_options:
                return value_str
            # Try case-insensitive match
            value_lower = value_str.lower()
            for option in question_options:
                if option.lower() == value_lower:
                    return option

            raise ValueError(
                f"Invalid option: '{value_str}'. "
                f"Valid options: {', '.join(question_options)}"
            )

        elif question_type == 'count':
            try:
                count_value = int(float(str(value).strip()))
                if count_value < 0:
                    raise ValueError("Count cannot be negative")
                return count_value
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid count value: '{value}'. Must be a non-negative integer."
                )

        elif question_type == 'text':
            return str(value).strip()

        else:
            raise ValueError(f"Unknown question type: {question_type}")
