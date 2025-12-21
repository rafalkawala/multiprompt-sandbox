from functools import lru_cache
from typing import Optional, Tuple, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryCallState
import httpx
import structlog
import os

from core.config import settings
from infrastructure.llm.gemini import GeminiProvider
from infrastructure.llm.vertex import VertexAIProvider
from infrastructure.llm.openai import OpenAIProvider
from infrastructure.llm.anthropic import AnthropicProvider

logger = structlog.get_logger(__name__)

def is_retryable_error(exception):
    """Return True if exception should be retried (429 rate limit or 5xx server errors)"""
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on rate limiting (429) and server errors (500-599)
        return status_code == 429 or (500 <= status_code < 600)
    return False

class LLMService:
    def __init__(self):
        self._providers = {
            "gemini": GeminiProvider(),
            "vertex": VertexAIProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider()
        }

    def _create_retry_decorator(self, retry_config: Optional[Dict[str, Any]]):
        """Create a retry decorator with model-specific configuration"""
        # Default retry configuration
        max_attempts = 5
        initial_wait = 2
        max_wait = 30
        exponential_base = 2

        # Override with model-specific config if provided
        if retry_config:
            max_attempts = retry_config.get('max_attempts', max_attempts)
            initial_wait = retry_config.get('initial_wait', initial_wait)
            max_wait = retry_config.get('max_wait', max_wait)
            exponential_base = retry_config.get('exponential_base', exponential_base)

        def log_retry(retry_state: RetryCallState):
            """Log retry attempts with structured logging"""
            if retry_state.outcome and retry_state.outcome.failed:
                exception = retry_state.outcome.exception()
                status_code = exception.response.status_code if isinstance(exception, httpx.HTTPStatusError) else None
                wait_time = retry_state.next_action.sleep if retry_state.next_action else 0

                logger.warning(
                    "llm_retry_attempt",
                    attempt=retry_state.attempt_number,
                    max_attempts=max_attempts,
                    status_code=status_code,
                    wait_seconds=round(wait_time, 1),
                    error_type=type(exception).__name__
                )

        return retry(
            retry=retry_if_exception(is_retryable_error),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait, exp_base=exponential_base),
            before_sleep=log_retry,
            reraise=True
        )

    async def generate_content(
        self,
        provider_name: str,
        api_key: Optional[str],
        auth_type: Optional[str],
        model_name: str,
        prompt: str,
        image_data: Optional[str] = None,
        mime_type: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        retry_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int, Dict[str, Any]]:

        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Secret Injection: Fallback to env vars if key is missing/placeholder
        final_api_key = api_key
        if not final_api_key or final_api_key == "sk-placeholder":
            if provider_name == "openai":
                final_api_key = os.environ.get("OPENAI_API_KEY")
            elif provider_name == "anthropic":
                final_api_key = os.environ.get("ANTHROPIC_API_KEY")
            elif provider_name == "gemini":
                # Gemini provider uses API key authentication only
                final_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            elif provider_name == "vertex":
                # Vertex AI provider uses API key or ADC
                final_api_key = os.environ.get("VERTEX_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")

            if final_api_key:
                logger.info("using_env_api_key", provider=provider_name)

        # Create retry-wrapped function with model-specific config
        retry_decorator = self._create_retry_decorator(retry_config)

        @retry_decorator
        async def _call_provider():
            return await provider.generate_content(
                api_key=final_api_key,
                auth_type=auth_type,
                model_name=model_name,
                image_data=image_data,
                mime_type=mime_type,
                prompt=prompt,
                system_message=system_message,
                temperature=temperature,
                max_tokens=max_tokens
            )

        return await _call_provider()

@lru_cache()
def get_llm_service() -> LLMService:
    return LLMService()
