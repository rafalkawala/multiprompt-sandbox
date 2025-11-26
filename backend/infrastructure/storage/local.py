import os
import shutil
from typing import Union, BinaryIO, Tuple
from fastapi import UploadFile, HTTPException
from core.interfaces.storage import IStorageProvider
from core.config import settings

class LocalStorageProvider(IStorageProvider):
    def __init__(self):
        self.base_dir = settings.UPLOAD_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, path: str) -> str:
        # Remove leading slash if present to ensure join works correctly
        if path.startswith("/"):
            path = path[1:]
        return os.path.join(self.base_dir, path)

    async def upload(self, file: Union[UploadFile, BinaryIO], destination_path: str) -> Tuple[str, int]:
        full_path = self._get_full_path(destination_path)
        directory = os.path.dirname(full_path)
        os.makedirs(directory, exist_ok=True)

        file_size = 0

        if isinstance(file, UploadFile):
            # Reset file pointer to beginning
            await file.seek(0)
            with open(full_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # 1MB chunks
                    file_size += len(content)
                    if settings.MAX_UPLOAD_SIZE and file_size > settings.MAX_UPLOAD_SIZE:
                        buffer.close()
                        if os.path.exists(full_path):
                             os.remove(full_path)
                        raise HTTPException(status_code=413, detail=f"File too large (limit {settings.MAX_UPLOAD_SIZE} bytes)")
                    buffer.write(content)
        else:
            # Assume BinaryIO
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            file_size = os.path.getsize(full_path)
        
        return destination_path, file_size

    async def delete(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    async def get_url(self, path: str) -> str:
        # Local storage doesn't support generating public URLs directly 
        # (requires API routing knowledge)
        raise NotImplementedError("Local storage does not support generating public URLs")

    async def download(self, path: str) -> bytes:
        full_path = self._get_full_path(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(full_path, "rb") as f:
            return f.read()

    async def exists(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        return os.path.exists(full_path)