"""
Service for importing and validating CSV annotations
"""
import pandas as pd
from typing import Optional, Dict, List, Any
from io import BytesIO
from sqlalchemy.orm import Session
import structlog

from models.project import Project, Dataset
from models.image import Image, Annotation

logger = structlog.get_logger(__name__)


class AnnotationImportService:
    """Service for importing and validating CSV annotations"""

    # Binary label normalization sets (case insensitive)
    BINARY_TRUE_VALUES = {'yes', 'y', 'true', 't', '1', '1.0'}
    BINARY_FALSE_VALUES = {'no', 'n', 'false', 'f', '0', '0.0'}

    def __init__(self, project: Project, dataset: Dataset, db_session: Session):
        self.project = project
        self.dataset = dataset
        self.db = db_session
        # Track filename usage for handling duplicates
        self._filename_usage_count = {}

    def normalize_binary(self, value: Any) -> Optional[bool]:
        """
        Normalize binary value to True/False/None.

        Accepts: yes/no, y/n, true/false, t/f, 1/0 (case insensitive)
        Returns: True, False, or None (for empty/missing)
        Raises: ValueError for invalid values
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
        Validate and normalize annotation value based on project question type.

        Args:
            value: The raw annotation value from CSV
            question_type: Type of question (binary, multiple_choice, count, text)
            question_options: List of valid options for multiple_choice questions

        Returns:
            Normalized value ready for database storage

        Raises:
            ValueError: If value is invalid for the question type
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
            # Text accepts almost anything
            return str(value).strip()

        else:
            raise ValueError(f"Unknown question type: {question_type}")

    def find_image(self, row: Dict) -> Optional[Image]:
        """
        Find image by ID or filename.

        Tries image_id first (safer), then falls back to filename match.
        For duplicate filenames, matches in sorted order (by filename, then ID).
        """
        # Try by image_id
        image_id = row.get('image_id')
        if image_id and not pd.isna(image_id):
            image = self.db.query(Image).filter(
                Image.id == str(image_id),
                Image.dataset_id == self.dataset.id
            ).first()
            if image:
                return image

        # Fall back to filename
        filename = row.get('image_filename')
        if filename and not pd.isna(filename):
            filename = str(filename).strip()

            # Find all images with this filename, sorted by filename then ID
            images = self.db.query(Image).filter(
                Image.filename == filename,
                Image.dataset_id == self.dataset.id
            ).order_by(Image.filename, Image.id).all()

            if not images:
                return None

            # Track how many times we've used this filename
            usage_count = self._filename_usage_count.get(filename, 0)

            # Return the next image in sorted order
            if usage_count < len(images):
                self._filename_usage_count[filename] = usage_count + 1
                return images[usage_count]
            else:
                # All images with this filename have been used
                # Return None to indicate no match (will show error)
                return None

        return None

    def validate_row(self, row: Dict, row_number: int) -> Dict:
        """
        Validate a single row and return validation result.

        Args:
            row: Dictionary containing CSV row data
            row_number: Row number in CSV (for error reporting)

        Returns:
            Dictionary with validation result including status, errors, warnings
        """
        result = {
            'row_number': row_number,
            'image_filename': row.get('image_filename', ''),
            'annotation_value': row.get('annotation_value', ''),
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'normalized_value': None,
            'image_id': None,
            'action': None  # 'create', 'update', or 'skip'
        }

        # Find image
        image = self.find_image(row)
        if not image:
            result['status'] = 'error'
            result['errors'].append('Image not found in dataset')
            return result

        result['image_id'] = str(image.id)

        # Check if value is empty (skip)
        annotation_value = row.get('annotation_value')
        if pd.isna(annotation_value) or annotation_value == '':
            result['action'] = 'skip'
            result['warnings'].append('Empty annotation value - will skip')
            return result

        # Validate annotation value
        try:
            normalized = self.validate_value(
                annotation_value,
                self.project.question_type,
                self.project.question_options
            )
            result['normalized_value'] = normalized

            # Determine action
            if image.annotation:
                result['action'] = 'update'
                result['warnings'].append('Will overwrite existing annotation')
            else:
                result['action'] = 'create'

        except ValueError as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        return result

    def validate_csv(self, file_bytes: bytes) -> Dict:
        """
        Validate entire CSV and return preview summary.

        Args:
            file_bytes: CSV file content as bytes

        Returns:
            Dictionary with validation summary and detailed results
        """
        # Reset filename usage tracking for this validation run
        self._filename_usage_count = {}

        try:
            # Read CSV with pandas
            df = pd.read_csv(BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

        # Check required columns
        required_cols = {'image_filename', 'annotation_value'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

        # Validate each row
        results = []
        for idx, row in df.iterrows():
            result = self.validate_row(row.to_dict(), idx + 2)  # +2 for header and 0-index
            results.append(result)

        # Generate summary
        summary = {
            'total_rows': len(results),
            'valid': sum(1 for r in results if r['status'] == 'valid'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'warnings': sum(1 for r in results if r['warnings']),
            'create': sum(1 for r in results if r['action'] == 'create'),
            'update': sum(1 for r in results if r['action'] == 'update'),
            'skip': sum(1 for r in results if r['action'] == 'skip'),
            'results': results
        }

        return summary

    def apply_import(self, file_bytes: bytes, user_id: str) -> Dict:
        """
        Apply CSV import to database.

        Args:
            file_bytes: CSV file content as bytes
            user_id: ID of user performing the import

        Returns:
            Dictionary with import results
        """
        # Validate first
        preview = self.validate_csv(file_bytes)

        if preview['errors'] > 0:
            raise ValueError(f"Cannot import: {preview['errors']} validation errors found")

        # Apply changes
        created = 0
        updated = 0
        skipped = 0

        for result in preview['results']:
            if result['status'] != 'valid':
                continue

            if result['action'] == 'skip':
                skipped += 1
                continue

            image_id = result['image_id']
            normalized_value = result['normalized_value']

            # Find or create annotation
            annotation = self.db.query(Annotation).filter(
                Annotation.image_id == image_id
            ).first()

            if annotation:
                # Update existing
                annotation.answer_value = {'value': normalized_value}
                annotation.annotator_id = user_id
                updated += 1
            else:
                # Create new
                annotation = Annotation(
                    image_id=image_id,
                    answer_value={'value': normalized_value},
                    annotator_id=user_id
                )
                self.db.add(annotation)
                created += 1

        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'total': created + updated
        }
