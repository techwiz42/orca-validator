"""Blob storage. Local-volume implementation now; an S3/Spaces adapter slots in behind
the same put/path/get interface later."""
import uuid
from pathlib import Path

from backend.app.config import get_settings


class LocalBlobStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, suffix: str = ".pdf") -> str:
        key = f"{uuid.uuid4().hex}{suffix}"
        (self.root / key).write_bytes(data)
        return key

    def path(self, key: str) -> str:
        return str(self.root / key)

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


_store: LocalBlobStore | None = None


def get_blob_store() -> LocalBlobStore:
    global _store
    if _store is None:
        _store = LocalBlobStore(get_settings().STORAGE_DIR)
    return _store
