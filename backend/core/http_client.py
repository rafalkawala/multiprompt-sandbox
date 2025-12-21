import httpx
import structlog
import asyncio

logger = structlog.get_logger(__name__)

class HttpClient:
    _clients = {}

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None # Should not happen in async context

        if loop not in cls._clients or cls._clients[loop].is_closed:
            # Clean up closed client if it exists but is closed
            if loop in cls._clients:
                del cls._clients[loop]

            logger.info(f"Initializing HTTP client for loop {id(loop)}")
            cls._clients[loop] = httpx.AsyncClient(timeout=60.0)

        return cls._clients[loop]

    @classmethod
    async def close(cls):
        """Close client for current loop"""
        try:
            loop = asyncio.get_running_loop()
            if loop in cls._clients:
                logger.info(f"Closing HTTP client for loop {id(loop)}")
                await cls._clients[loop].aclose()
                del cls._clients[loop]
        except RuntimeError:
            pass

    @classmethod
    async def close_all(cls):
        """Close all clients (e.g. on shutdown)"""
        for loop, client in list(cls._clients.items()):
            if not client.is_closed:
                try:
                    await client.aclose()
                except Exception as e:
                    logger.warning(f"Error closing client for loop {id(loop)}: {e}")
        cls._clients.clear()
