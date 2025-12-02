from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from google.cloud import storage
import logging
import re

logger = logging.getLogger(__name__)

# Supported image extensions
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']

@dataclass
class GCSFileInfo:
    """Information about a file in GCS"""
    bucket_name: str
    blob_name: str
    full_path: str  # gs://bucket/path
    filename: str
    size: int
    time_created: datetime
    content_type: str


class GCSScannerService:
    """Service for scanning and copying files from GCS folders"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> storage.Client:
        """Lazy initialize GCS client"""
        if self._client is None:
            try:
                self._client = storage.Client()
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._client

    def parse_gcs_path(self, gcs_path: str) -> Tuple[str, str]:
        """
        Parse a GCS path into bucket name and prefix.

        Args:
            gcs_path: Path in format gs://bucket-name/optional/prefix

        Returns:
            Tuple of (bucket_name, prefix)

        Raises:
            ValueError: If path format is invalid
        """
        if not gcs_path.startswith('gs://'):
            raise ValueError(f"GCS path must start with gs://. Got: {gcs_path}")

        # Remove gs:// prefix
        path_without_scheme = gcs_path[5:]

        # Split into bucket and prefix
        parts = path_without_scheme.split('/', 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        # Ensure prefix doesn't start with /
        prefix = prefix.lstrip('/')

        if not bucket_name:
            raise ValueError(f"Invalid GCS path: {gcs_path}. Bucket name is required.")

        return bucket_name, prefix

    def scan_folder(
        self,
        gcs_folder_path: str,
        last_processed_timestamp: Optional[datetime] = None,
        allowed_extensions: Optional[List[str]] = None
    ) -> List[GCSFileInfo]:
        """
        Scan a GCS folder for files, optionally filtering by timestamp.

        Args:
            gcs_folder_path: GCS path to scan (gs://bucket/prefix)
            last_processed_timestamp: If provided, only return files created after this time minus 1 minute buffer
            allowed_extensions: List of allowed file extensions (default: image extensions)

        Returns:
            List of GCSFileInfo objects, sorted by time_created ascending
        """
        if allowed_extensions is None:
            allowed_extensions = ALLOWED_EXTENSIONS

        # Parse GCS path
        bucket_name, prefix = self.parse_gcs_path(gcs_folder_path)

        # Get bucket
        bucket = self.client.bucket(bucket_name)

        # Calculate cutoff time with 1-minute buffer
        cutoff_time = None
        if last_processed_timestamp:
            cutoff_time = last_processed_timestamp - timedelta(minutes=1)

        # List blobs
        blobs = bucket.list_blobs(prefix=prefix)

        file_infos = []
        for blob in blobs:
            # Skip if blob name is exactly the prefix (folder marker)
            if blob.name == prefix or blob.name.endswith('/'):
                continue

            # Check extension
            ext = self._get_file_extension(blob.name)
            if ext.lower() not in allowed_extensions:
                logger.debug(f"Skipping {blob.name}: extension {ext} not allowed")
                continue

            # Check timestamp
            if cutoff_time and blob.time_created <= cutoff_time:
                logger.debug(f"Skipping {blob.name}: created at {blob.time_created}, cutoff is {cutoff_time}")
                continue

            # Extract filename from blob name
            filename = blob.name.split('/')[-1]

            file_info = GCSFileInfo(
                bucket_name=bucket_name,
                blob_name=blob.name,
                full_path=f"gs://{bucket_name}/{blob.name}",
                filename=filename,
                size=blob.size,
                time_created=blob.time_created,
                content_type=blob.content_type or 'application/octet-stream'
            )
            file_infos.append(file_info)

        # Sort by time_created ascending
        file_infos.sort(key=lambda x: x.time_created)

        logger.info(f"Scanned {gcs_folder_path}: found {len(file_infos)} new files")
        return file_infos

    def copy_blob(
        self,
        source_path: str,
        destination_bucket_name: str,
        destination_blob_name: str
    ) -> Tuple[str, int]:
        """
        Copy a blob from one location to another.

        Args:
            source_path: Source GCS path (gs://bucket/path)
            destination_bucket_name: Destination bucket name
            destination_blob_name: Destination blob name (path within bucket)

        Returns:
            Tuple of (destination_path, size_in_bytes)
        """
        # Parse source path
        source_bucket_name, source_blob_name = self.parse_gcs_path(source_path)

        # Get buckets
        source_bucket = self.client.bucket(source_bucket_name)
        destination_bucket = self.client.bucket(destination_bucket_name)

        # Get source blob
        source_blob = source_bucket.blob(source_blob_name)

        if not source_blob.exists():
            raise FileNotFoundError(f"Source blob not found: {source_path}")

        # Copy to destination
        destination_blob = source_bucket.copy_blob(
            source_blob,
            destination_bucket,
            destination_blob_name
        )

        logger.info(f"Copied {source_path} to gs://{destination_bucket_name}/{destination_blob_name}")
        return f"gs://{destination_bucket_name}/{destination_blob_name}", destination_blob.size

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' not in filename:
            return ''
        return '.' + filename.rsplit('.', 1)[1]
