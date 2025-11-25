from functools import lru_cache
from backend.core.config import settings
from backend.core.interfaces.storage import IStorageProvider
from backend.infrastructure.storage.local import LocalStorageProvider
from backend.infrastructure.storage.gcs import GCSStorageProvider

@lru_cache()
def get_storage_provider() -> IStorageProvider:
    """
    Factory function to get the configured storage provider.
    """
    if settings.STORAGE_TYPE == "gcs":
        return GCSStorageProvider()
    else:
        return LocalStorageProvider()
