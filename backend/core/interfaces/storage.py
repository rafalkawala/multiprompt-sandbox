from abc import ABC, abstractmethod
from fastapi import UploadFile
from typing import BinaryIO, Union, Tuple

class IStorageProvider(ABC):
    """Abstract interface for file storage operations."""

    @abstractmethod
    async def upload(self, file: Union[UploadFile, BinaryIO], destination_path: str) -> Tuple[str, int]:
        """
        Uploads a file to the storage provider.
        
        Args:
            file: The file object to upload. Can be a FastAPI UploadFile or a binary file-like object.
            destination_path: The relative path where the file should be stored.
            
        Returns:
            A tuple containing (uploaded_path, file_size_in_bytes).
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Deletes a file from the storage provider.
        
        Args:
            path: The relative path of the file to delete.
            
        Returns:
            True if deletion was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """
        Gets the public URL for a file.
        
        Args:
            path: The relative path of the file.
            
        Returns:
            The public URL.
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """
        Downloads the file content as bytes.
        
        Args:
            path: The relative path of the file.
            
        Returns:
            The file content as bytes.
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Checks if a file exists.
        
        Args:
            path: The relative path of the file.
            
        Returns:
            True if the file exists, False otherwise.
        """
        pass
