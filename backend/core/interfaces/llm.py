from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any

class ILLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate_content(
        self,
        api_key: Optional[str],
        auth_type: Optional[str],
        model_name: str,
        image_data: Optional[str],
        mime_type: Optional[str],
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, int, Dict[str, Any]]:
        """
        Generates content from the LLM.

        Args:
            api_key: API Key for the provider.
            auth_type: Authentication type (e.g., 'api_key', 'google_adc').
            model_name: Name of the model to use.
            image_data: Base64 encoded image data (optional).
            mime_type: Mime type of the image (optional).
            prompt: The user prompt.
            system_message: Optional system message.
            temperature: Temperature parameter.
            max_tokens: Max output tokens.

        Returns:
            A tuple containing (generated_text, latency_in_ms, usage_metadata).
            usage_metadata contains: prompt_tokens, completion_tokens, total_tokens
        """
        pass

    @abstractmethod
    def estimate_cost(
        self,
        input_text: str,
        output_est_text: str,
        images: list[str],
        pricing_config: Dict[str, Any]
    ) -> float:
        """
        Estimate the cost of a request based on inputs and pricing config.

        Args:
            input_text: The input text prompt.
            output_est_text: Estimated output text.
            images: List of base64 encoded images.
            pricing_config: Pricing configuration dictionary.

        Returns:
            Estimated cost in USD.
        """
        pass

    @abstractmethod
    def calculate_actual_cost(
        self,
        usage_metadata: Dict[str, Any],
        pricing_config: Dict[str, Any],
        has_image: bool = False
    ) -> float:
        """
        Calculate actual cost based on usage metadata returned by the API.

        Args:
            usage_metadata: Metadata containing token counts (prompt_tokens, completion_tokens).
            pricing_config: Pricing configuration dictionary.
            has_image: Whether the request included an image (relevant for some providers).

        Returns:
            Actual cost in USD.
        """
        pass
