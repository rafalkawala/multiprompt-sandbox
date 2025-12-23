"""
Tests for LLM service module
Located at: backend/services/llm_service.py

These tests cover LLM provider routing and content generation.
All LLM provider calls are mocked to avoid real API calls.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Import what we're testing
from services.llm_service import LLMService, get_llm_service


class TestLLMService:
    """Test LLM service provider routing"""

    @pytest.mark.asyncio
    async def test_generate_content_gemini_provider(self, mocker):
        """
        Test that LLMService routes to Gemini provider correctly

        Expected: Gemini provider is called with correct parameters
        """
        # Arrange
        service = LLMService()

        # Mock the Gemini provider
        mock_gemini = mocker.AsyncMock()
        mock_gemini.generate_content.return_value = ("Gemini response", 50, {"model": "gemini-pro"})
        service._providers["gemini"] = mock_gemini

        # Act
        result = await service.generate_content(
            provider_name="gemini",
            api_key="test-api-key",
            auth_type="api_key",
            model_name="gemini-pro",
            prompt="test prompt"
        )

        # Assert
        assert result == ("Gemini response", 50, {"model": "gemini-pro"})
        mock_gemini.generate_content.assert_called_once_with(
            api_key="test-api-key",
            auth_type="api_key",
            model_name="gemini-pro",
            image_data=None,
            mime_type=None,
            prompt="test prompt",
            system_message=None,
            temperature=0.0,
            max_tokens=1024
        )

    @pytest.mark.asyncio
    async def test_generate_content_openai_provider(self, mocker):
        """
        Test that LLMService routes to OpenAI provider correctly

        Expected: OpenAI provider is called with correct parameters
        """
        # Arrange
        service = LLMService()

        # Mock the OpenAI provider
        mock_openai = mocker.AsyncMock()
        mock_openai.generate_content.return_value = ("OpenAI response", 75, {"model": "gpt-4"})
        service._providers["openai"] = mock_openai

        # Act
        result = await service.generate_content(
            provider_name="openai",
            api_key="sk-test-key",
            auth_type="api_key",
            model_name="gpt-4",
            prompt="analyze this",
            temperature=0.7
        )

        # Assert
        assert result == ("OpenAI response", 75, {"model": "gpt-4"})
        mock_openai.generate_content.assert_called_once()
        # Verify temperature was passed correctly
        call_args = mock_openai.generate_content.call_args
        assert call_args[1]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_generate_content_anthropic_provider(self, mocker):
        """
        Test that LLMService routes to Anthropic provider correctly

        Expected: Anthropic provider is called with correct parameters
        """
        # Arrange
        service = LLMService()

        # Mock the Anthropic provider
        mock_anthropic = mocker.AsyncMock()
        mock_anthropic.generate_content.return_value = ("Claude response", 100, {"model": "claude-3"})
        service._providers["anthropic"] = mock_anthropic

        # Act
        result = await service.generate_content(
            provider_name="anthropic",
            api_key="sk-ant-test",
            auth_type="api_key",
            model_name="claude-3",
            prompt="test prompt",
            system_message="You are a helpful assistant"
        )

        # Assert
        assert result == ("Claude response", 100, {"model": "claude-3"})
        mock_anthropic.generate_content.assert_called_once()
        # Verify system message was passed
        call_args = mock_anthropic.generate_content.call_args
        assert call_args[1]["system_message"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_generate_content_unknown_provider_raises_error(self):
        """
        Test that LLMService raises ValueError for unknown providers

        Expected: ValueError with descriptive message
        """
        # Arrange
        service = LLMService()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.generate_content(
                provider_name="unknown-provider",
                api_key="test-key",
                auth_type="api_key",
                model_name="some-model",
                prompt="test"
            )

        assert "Unknown provider: unknown-provider" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_content_passes_image_parameters(self, mocker):
        """
        Test that image data and mime type are passed correctly to providers

        Expected: Provider receives image_data and mime_type parameters
        """
        # Arrange
        service = LLMService()

        # Mock the Gemini provider (supports vision)
        mock_gemini = mocker.AsyncMock()
        mock_gemini.generate_content.return_value = ("Image analysis", 120, {"model": "gemini-pro-vision"})
        service._providers["gemini"] = mock_gemini

        # Act
        result = await service.generate_content(
            provider_name="gemini",
            api_key="test-key",
            auth_type="api_key",
            model_name="gemini-pro-vision",
            prompt="What's in this image?",
            image_data="base64-encoded-image-data",
            mime_type="image/jpeg"
        )

        # Assert
        assert result == ("Image analysis", 120, {"model": "gemini-pro-vision"})
        mock_gemini.generate_content.assert_called_once()
        call_args = mock_gemini.generate_content.call_args
        assert call_args[1]["image_data"] == "base64-encoded-image-data"
        assert call_args[1]["mime_type"] == "image/jpeg"


class TestGetLLMService:
    """Test LLM service singleton factory"""

    def test_get_llm_service_returns_instance(self):
        """
        Test that get_llm_service returns an LLMService instance

        Expected: Instance of LLMService is returned
        """
        # Act
        service = get_llm_service()

        # Assert
        assert isinstance(service, LLMService)
        assert hasattr(service, '_providers')
        assert 'gemini' in service._providers
        assert 'openai' in service._providers
        assert 'anthropic' in service._providers

    def test_get_llm_service_is_cached(self):
        """
        Test that get_llm_service returns the same instance (caching)

        Expected: Multiple calls return the exact same instance (lru_cache)
        """
        # Act
        service1 = get_llm_service()
        service2 = get_llm_service()

        # Assert
        assert service1 is service2  # Same object in memory


# ============================================================================
# TODO: Add more LLM service tests (Priority: MEDIUM)
# ============================================================================
#
# Add these tests to increase coverage to 90%+:
#
# 1. test_generate_content_with_max_tokens()
#    - Test max_tokens parameter is passed correctly
#
# 2. test_generate_content_with_all_parameters()
#    - Test all optional parameters together
#
# 3. test_provider_error_propagates()
#    - Test that provider errors are propagated correctly
#
# 4. test_generate_content_returns_tuple()
#    - Test return value format (text, token_count)
#
# 5. test_multiple_providers_can_be_used_sequentially()
#    - Test switching between providers in same service instance
#
# See TESTING_GUIDE.md for examples and patterns to follow.
# ============================================================================
