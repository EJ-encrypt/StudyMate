"""Where uploaded lecture files live.

Production uses a private Supabase Storage bucket. The browser uploads to it
directly with a short-lived signed URL the API hands out, because Vercel
rejects request bodies over 4.5MB and lecture slides regularly exceed that.
The API itself only ever reads files back, with the service-role key.

Without Supabase configured (local development, tests) files go to a folder
on disk, and the "signed URL" points at a small upload endpoint on the API.
"""

import base64
import hashlib
import hmac
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, quote, urlparse

import httpx

from app.core.config import settings


class StorageError(RuntimeError):
    pass


class FileMissing(StorageError):
    """The object was never uploaded, or has been removed."""


@dataclass(frozen=True)
class UploadTarget:
    # "supabase": upload with supabase-js `uploadToSignedUrl(path, token, file)`.
    # "local": PUT the raw file to `url` on the API.
    method: str
    path: str
    token: str
    url: str


class SupabaseStorage:
    def __init__(self) -> None:
        self._base = f"{settings.supabase_url.rstrip('/')}/storage/v1"
        self._bucket = settings.storage_bucket
        key = settings.supabase_service_role_key
        self._headers = {"Authorization": f"Bearer {key}", "apikey": key}

    def _object(self, path: str) -> str:
        return quote(path, safe="/")

    def create_upload(self, path: str) -> UploadTarget:
        response = httpx.post(
            f"{self._base}/object/upload/sign/{self._bucket}/{self._object(path)}",
            headers=self._headers,
            timeout=15,
        )
        if response.status_code >= 400:
            raise StorageError(f"Could not create an upload URL ({response.status_code}): {response.text}")
        signed = response.json()["url"]
        token = parse_qs(urlparse(signed).query).get("token", [""])[0]
        return UploadTarget(method="supabase", path=path, token=token, url=f"{self._base}{signed}")

    def upload(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        response = httpx.post(
            f"{self._base}/object/{self._bucket}/{self._object(path)}",
            headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
            content=data,
            timeout=60,
        )
        if response.status_code >= 400:
            raise StorageError(f"Upload failed ({response.status_code}): {response.text}")

    def download(self, path: str) -> bytes:
        response = httpx.get(
            f"{self._base}/object/authenticated/{self._bucket}/{self._object(path)}",
            headers=self._headers,
            timeout=60,
        )
        if response.status_code in (400, 404):
            raise FileMissing(path)
        if response.status_code >= 400:
            raise StorageError(f"Download failed ({response.status_code}): {response.text}")
        return response.content

    def delete(self, paths: list[str]) -> None:
        # The API takes up to a thousand objects per call.
        for start in range(0, len(paths), 1000):
            response = httpx.request(
                "DELETE",
                f"{self._base}/object/{self._bucket}",
                headers=self._headers,
                json={"prefixes": paths[start : start + 1000]},
                timeout=60,
            )
            if response.status_code >= 400:
                raise StorageError(f"Delete failed ({response.status_code}): {response.text}")


def _sign(path: str) -> str:
    key = (settings.cron_secret or settings.supabase_jwt_secret or "local-dev").encode()
    return hmac.new(key, path.encode(), hashlib.sha256).hexdigest()


class LocalStorage:
    """Disk-backed stand-in, for development and tests only."""

    @property
    def _root(self) -> Path:
        # Read on use rather than cached, so tests can point it elsewhere.
        return Path(settings.storage_dir)

    def _resolve(self, path: str) -> Path:
        # Rows written before the move to object storage hold a full disk path.
        candidate = Path(path)
        if candidate.is_file():
            return candidate
        resolved = (self._root / path).resolve()
        if self._root.resolve() not in resolved.parents:
            raise StorageError("Path escapes the storage directory")
        return resolved

    def create_upload(self, path: str) -> UploadTarget:
        encoded = base64.urlsafe_b64encode(path.encode()).decode()
        token = f"{encoded}.{_sign(path)}"
        return UploadTarget(method="local", path=path, token=token, url=f"/storage/local/{token}")

    @staticmethod
    def verify_token(token: str) -> str | None:
        encoded, _, signature = token.partition(".")
        try:
            path = base64.urlsafe_b64decode(encoded.encode()).decode()
        except ValueError:
            return None
        return path if hmac.compare_digest(signature, _sign(path)) else None

    def upload(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def download(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.is_file():
            raise FileMissing(path)
        return target.read_bytes()

    def delete(self, paths: list[str]) -> None:
        for path in paths:
            target = self._resolve(path)
            if target.is_file():
                target.unlink()


@lru_cache
def get_storage() -> SupabaseStorage | LocalStorage:
    if settings.uses_supabase_storage:
        return SupabaseStorage()
    return LocalStorage()


@contextmanager
def local_copy(path: str) -> Iterator[str]:
    """Download a stored file to a temporary path the extractors can open.

    The extractors dispatch on the file extension, so the temporary file keeps
    it. On Vercel only /tmp is writable, which is where tempfile puts it.
    """
    data = get_storage().download(path)
    suffix = Path(path).suffix
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / f"source{suffix}"
        target.write_bytes(data)
        yield str(target)
