from functools import lru_cache

from core import config
from storage.base import ObjectStorage
from storage.local import LocalObjectStorage


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    backend = config.STORAGE_BACKEND
    if backend == "local":
        return LocalObjectStorage(config.LOCAL_STORAGE_DIR)
    # S3 アダプタは AWS 移行（#128）で追加する。それまでは未対応値を明示的に弾く。
    raise ValueError(f"Unsupported STORAGE_BACKEND: {backend!r}")


__all__ = ["ObjectStorage", "get_storage"]
