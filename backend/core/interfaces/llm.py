from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any

class ILLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate_content(
        self,
        api_key: Optional[str],
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
