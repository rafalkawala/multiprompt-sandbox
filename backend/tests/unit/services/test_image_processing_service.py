import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session
from services.image_processing_service import ImageProcessingService
from models.image import Image
from models.project import Dataset
from core.domain.embedding.schema import EmbeddingResponse

@pytest.fixture
def mock_storage():
    return AsyncMock()

@pytest.fixture
def mock_embedding_service():
    return AsyncMock()

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def service(mock_storage, mock_embedding_service):
    with patch("services.image_processing_service.get_storage_provider", return_value=mock_storage), \
         patch("services.image_processing_service.get_embedding_service", return_value=mock_embedding_service):
        return ImageProcessingService()

@pytest.mark.asyncio
async def test_process_dataset_images_success(service, mock_db, mock_storage, mock_embedding_service):
    # Setup
    dataset_id = "test-dataset-id"
    dataset = Dataset(id=dataset_id, processing_status="pending", failed_files=0, processed_files=0)
    image = Image(id="image-1", dataset_id=dataset_id, processing_status="pending", storage_path="gs://test/image.jpg", filename="image.jpg")

    mock_db.query.return_value.filter.return_value.first.return_value = dataset
    mock_db.query.return_value.filter.return_value.all.return_value = [image]

    mock_storage.download.return_value = b"fake_image_bytes"

    # Mock embedding response
    embedding_response = EmbeddingResponse(image_embedding=[0.1, 0.2, 0.3], dimension=3)
    mock_embedding_service.generate_embeddings.return_value = embedding_response

    # Mock generate_thumbnail
    with patch("services.image_processing_service.generate_thumbnail", return_value=b"fake_thumbnail_bytes"):
        await service.process_dataset_images(dataset_id, mock_db)

    # Verify interactions
    mock_storage.download.assert_called_with("gs://test/image.jpg")
    mock_embedding_service.generate_embeddings.assert_called_with(image_bytes=b"fake_image_bytes")

    # Verify status updates
    assert image.processing_status == "completed"
    assert image.thumbnail_data == b"fake_thumbnail_bytes"
    assert image.embedding == [0.1, 0.2, 0.3]
    assert dataset.processed_files == 1
    assert dataset.processing_status == "completed"

@pytest.mark.asyncio
async def test_process_dataset_images_embedding_failure(service, mock_db, mock_storage, mock_embedding_service):
    # Setup
    dataset_id = "test-dataset-id"
    dataset = Dataset(id=dataset_id, processing_status="pending", failed_files=0, processed_files=0)
    image = Image(id="image-1", dataset_id=dataset_id, processing_status="pending", storage_path="gs://test/image.jpg", filename="image.jpg")

    mock_db.query.return_value.filter.return_value.first.return_value = dataset
    mock_db.query.return_value.filter.return_value.all.return_value = [image]

    mock_storage.download.return_value = b"fake_image_bytes"

    # Mock embedding failure
    mock_embedding_service.generate_embeddings.side_effect = Exception("Embedding API Error")

    # Mock generate_thumbnail
    with patch("services.image_processing_service.generate_thumbnail", return_value=b"fake_thumbnail_bytes"):
        await service.process_dataset_images(dataset_id, mock_db)

    # Verify interactions
    mock_storage.download.assert_called_with("gs://test/image.jpg")
    mock_embedding_service.generate_embeddings.assert_called_with(image_bytes=b"fake_image_bytes")

    # Verify status updates (should still be completed, just without embedding)
    assert image.processing_status == "completed"
    assert image.thumbnail_data == b"fake_thumbnail_bytes"
    assert image.embedding is None # Embedding should be None
    assert dataset.processed_files == 1
    assert dataset.processing_status == "completed"

@pytest.mark.asyncio
async def test_process_dataset_images_thumbnail_failure(service, mock_db, mock_storage, mock_embedding_service):
    # Setup
    dataset_id = "test-dataset-id"
    dataset = Dataset(id=dataset_id, processing_status="pending", failed_files=0, processed_files=0)
    image = Image(id="image-1", dataset_id=dataset_id, processing_status="pending", storage_path="gs://test/image.jpg", filename="image.jpg")

    mock_db.query.return_value.filter.return_value.first.return_value = dataset
    mock_db.query.return_value.filter.return_value.all.return_value = [image]

    mock_storage.download.return_value = b"fake_image_bytes"

    # Mock generate_thumbnail failure
    with patch("services.image_processing_service.generate_thumbnail", side_effect=Exception("Thumbnail Error")):
         await service.process_dataset_images(dataset_id, mock_db)

    # Verify interactions
    mock_storage.download.assert_called_with("gs://test/image.jpg")

    # Verify status updates (should be failed)
    assert image.processing_status == "failed"
    assert "Thumbnail Error" in image.processing_error
    assert dataset.failed_files == 1
    assert dataset.processing_status == "failed"
