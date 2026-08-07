import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()


class StorageService:
    def __init__(self) -> None:
        self.base_dir = Path(settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, original_filename: str) -> Path:
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return self.base_dir / unique_name

    async def save_upload(self, file: UploadFile) -> tuple[str, int]:
        """
        Stream an UploadFile to disk in chunks (avoids loading large files
        fully into memory). Returns (storage_path, size_in_bytes).
        """
        destination = self._safe_path(file.filename or "upload")
        size = 0
        chunk_size = 1024 * 1024  # 1 MB

        with open(destination, "wb") as out_file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                out_file.write(chunk)

        await file.seek(0)
        return str(destination), size

    def delete_file(self, storage_path: str) -> None:
        try:
            os.remove(storage_path)
        except FileNotFoundError:
            pass


storage_service = StorageService()
