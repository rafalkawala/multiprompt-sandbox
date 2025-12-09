import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.embedding_service import EmbeddingService

@pytest.fixture
def mock_google_provider():
    with patch("services.embedding_service.GoogleMultimodalEmbeddingProvider") as mock:
        yield mock

@pytest.mark.asyncio
async def test_generate_embeddings_text(mock_google_provider):
    # Setup
    provider_instance = mock_google_provider.return_value
    provider_instance.generate_embeddings = AsyncMock(return_value={
        "text_embedding": [0.1, 0.2, 0.3]
    })

    service = EmbeddingService()

    # Execute
    result = await service.generate_embeddings(text="Hello world")

    # Verify
    assert "text_embedding" in result
    assert result["text_embedding"] == [0.1, 0.2, 0.3]
    provider_instance.generate_embeddings.assert_called_once()
    call_args = provider_instance.generate_embeddings.call_args
    assert call_args.kwargs['text'] == "Hello world"
    assert call_args.kwargs['model_name'] == "multimodalembedding@001"

@pytest.mark.asyncio
async def test_generate_embeddings_image(mock_google_provider):
    # Setup
    provider_instance = mock_google_provider.return_value
    provider_instance.generate_embeddings = AsyncMock(return_value={
        "image_embedding": [0.4, 0.5, 0.6]
    })

    service = EmbeddingService()

    # Execute
    result = await service.generate_embeddings(image_path="gs://bucket/image.jpg")

    # Verify
    assert "image_embedding" in result
    assert result["image_embedding"] == [0.4, 0.5, 0.6]
    provider_instance.generate_embeddings.assert_called_once()
    call_args = provider_instance.generate_embeddings.call_args
    assert call_args.kwargs['image_path'] == "gs://bucket/image.jpg"

@pytest.mark.asyncio
async def test_generate_embeddings_invalid_provider():
    service = EmbeddingService()

    with pytest.raises(ValueError, match="Unknown embedding provider"):
        await service.generate_embeddings(text="test", provider_name="unknown")
