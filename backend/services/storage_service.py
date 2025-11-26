from functools import lru_cache
from core.config import settings
from core.interfaces.storage import IStorageProvider
from infrastructure.storage.local import LocalStorageProvider
from infrastructure.storage.gcs import GCSStorageProvider

@lru_cache()
def get_storage_provider() -> IStorageProvider:
    """
    Factory function to get the configured storage provider.
    """
    if settings.STORAGE_TYPE == "gcs":
        return GCSStorageProvider()
    else:
        return LocalStorageProvider()
