from functools import lru_cache
from typing import Optional, Tuple
import logging

from core.retry_utils import get_retry_decorator
from infrastructure.llm.gemini import GeminiProvider
from infrastructure.llm.openai import OpenAIProvider
from infrastructure.llm.anthropic import AnthropicProvider

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self._providers = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider()
        }

    @get_retry_decorator()
    async def generate_content(
        self,
        provider_name: str,
        api_key: Optional[str],
        model_name: str,
        prompt: str,
        image_data: Optional[str] = None,
        mime_type: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> Tuple[str, int]:
        
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return await provider.generate_content(
            api_key=api_key,
            model_name=model_name,
            image_data=image_data,
            mime_type=mime_type,
            prompt=prompt,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens
        )

@lru_cache()
def get_llm_service() -> LLMService:
    return LLMService()
