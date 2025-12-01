import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from infrastructure.storage.gcs import GCSStorageProvider

class MockUploadFileLike:
    """A class that looks like UploadFile but isn't an instance of it"""
    def __init__(self, content=b"test content"):
        self.file = BytesIO(content)
        self.content_type = "text/plain"
        self.filename = "test.txt"
        
    async def seek(self, pos):
        self.file.seek(pos)

@pytest.mark.asyncio
async def test_gcs_upload_duck_typing():
    """
    Test that GCSStorageProvider.upload handles objects that look like UploadFile
    (have a .file attribute) even if they aren't instances of the imported UploadFile class.
    This verifies the fix for the 'has no attribute tell' error.
    """
    # Mock the storage client and blob
    with patch('infrastructure.storage.gcs.storage.Client') as mock_client_cls:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        mock_client_cls.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.size = 123
        
        # Initialize provider
        provider = GCSStorageProvider()
        # Force init the bucket
        provider.bucket_name = "test-bucket"
        _ = provider.bucket 
        
        # Create a file-like object that mimics UploadFile but isn't one
        # (simulating the scenario where isinstance fails or it's a similar wrapper)
        upload_file_like = MockUploadFileLike()
        
        # Call upload
        await provider.upload(upload_file_like, "dest/path.txt")
        
        # Verify that upload_from_file was called with the underlying file object (BytesIO)
        # and NOT the wrapper object.
        # The wrapper object (MockUploadFileLike) does not have tell(), so passing it would fail in real life.
        # The underlying BytesIO DOES have tell().
        
        # Check arguments passed to upload_from_file
        args, kwargs = mock_blob.upload_from_file.call_args
        uploaded_obj = args[0]
        
        # It should be the BytesIO object, not the MockUploadFileLike object
        assert uploaded_obj is upload_file_like.file
        assert uploaded_obj is not upload_file_like
        
        # Verify content type was passed
        assert kwargs['content_type'] == "text/plain"
