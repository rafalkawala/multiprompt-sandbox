from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception
import httpx
import logging

logger = logging.getLogger(__name__)

# Try to import google exceptions
try:
    from google.api_core.exceptions import ResourceExhausted
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False
    ResourceExhausted = None

def is_retryable_error(exception: Exception) -> bool:
    """
    Check if the exception is a retryable rate limit error.
    Handles:
    - httpx.HTTPStatusError (429)
    - google.api_core.exceptions.ResourceExhausted (429)
    """
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code == 429

    if HAS_GOOGLE_API and isinstance(exception, ResourceExhausted):
        return True

    return False

def get_retry_decorator(stop_after: int = 3, wait_seconds: float = 2.0):
    """
    Returns a tenacity retry decorator configured for rate limits.
    """
    return retry(
        retry=retry_if_exception(is_retryable_error),
        stop=stop_after_attempt(stop_after),
        wait=wait_fixed(wait_seconds),
        before_sleep=lambda retry_state: logger.warning(
            f"Rate limit hit. Retrying... (Attempt {retry_state.attempt_number})"
        )
    )
