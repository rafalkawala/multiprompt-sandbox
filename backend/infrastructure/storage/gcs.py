from typing import Union, BinaryIO, Tuple
from fastapi import UploadFile
from google.cloud import storage
from datetime import timedelta
import structlog

from core.interfaces.storage import IStorageProvider
from core.config import settings

logger = structlog.get_logger(__name__)

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
        
        # Check if it's an UploadFile using duck typing to be more robust
        # (isinstance can fail with some import patterns or mocks)
        if isinstance(file, UploadFile) or hasattr(file, "file"):
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
        import asyncio
        import functools
        
        blob = self.bucket.blob(path)
        
        loop = asyncio.get_running_loop()
        
        # Check existence in thread pool to avoid blocking
        exists = await loop.run_in_executor(None, blob.exists)
        if not exists:
            raise FileNotFoundError(f"File not found in GCS: {path}")
            
        return await loop.run_in_executor(None, blob.download_as_bytes)

    async def exists(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        return blob.exists()