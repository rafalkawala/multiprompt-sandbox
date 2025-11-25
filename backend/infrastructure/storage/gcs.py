from typing import Union, BinaryIO, Tuple
from fastapi import UploadFile
from google.cloud import storage
from datetime import timedelta
import logging

from backend.core.interfaces.storage import IStorageProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)

class GCSStorageProvider(IStorageProvider):
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        self._client = None
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            if not self.bucket_name:
                raise ValueError("GCS_BUCKET_NAME is not configured")
            
            # Initialize client if needed
            if self._client is None:
                try:
                    self._client = storage.Client()
                except Exception as e:
                    logger.error(f"Failed to initialize GCS client: {e}")
                    raise

            self._bucket = self._client.bucket(self.bucket_name)
        return self._bucket

    async def upload(self, file: Union[UploadFile, BinaryIO], destination_path: str) -> Tuple[str, int]:
        blob = self.bucket.blob(destination_path)
        
        if isinstance(file, UploadFile):
            await file.seek(0)
            # stream upload
            blob.upload_from_file(
                file.file,
                content_type=file.content_type,
                timeout=120
            )
        else:
            blob.upload_from_file(file)
            
        blob.reload()
        return destination_path, blob.size

    async def delete(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        if blob.exists():
            blob.delete()
            return True
        return False

    async def get_url(self, path: str) -> str:
        blob = self.bucket.blob(path)
        if not blob.exists():
             raise FileNotFoundError(f"File not found in GCS: {path}")
             
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )

    async def download(self, path: str) -> bytes:
        blob = self.bucket.blob(path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in GCS: {path}")
            
        return blob.download_as_bytes()

    async def exists(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        return blob.exists()