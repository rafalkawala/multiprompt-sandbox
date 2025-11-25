import httpx
import logging

logger = logging.getLogger(__name__)

class HttpClient:
    _client: httpx.AsyncClient = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            logger.info("Initializing global HTTP client")
            cls._client = httpx.AsyncClient(timeout=60.0)
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            logger.info("Closing global HTTP client")
            await cls._client.aclose()
            cls._client = None
