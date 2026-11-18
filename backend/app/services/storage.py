"""
storage.py — Content-addressed local file storage (files are named by SHA-256).
Swap for an S3 implementation with the same interface in production.
"""

import hashlib
import os
from typing import Tuple

from fastapi import HTTPException, UploadFile

from app.config import settings

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class LocalStorageService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir if os.path.isabs(base_dir) else os.path.join(BACKEND_ROOT, base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_file(self, file: UploadFile, max_bytes: int | None = None) -> Tuple[str, str, int]:
        """Returns (file_path, sha256, size_in_bytes)."""
        content = await file.read()
        if max_bytes and len(content) > max_bytes:
            raise HTTPException(status_code=413, detail=f"File is larger than {max_bytes // (1024 * 1024)} MB.")
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        file_hash = hashlib.sha256(content).hexdigest()
        ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
        file_path = os.path.join(self.base_dir, f"{file_hash}{ext}")
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(content)
        await file.seek(0)
        return file_path, file_hash, len(content)


storage_service = LocalStorageService(settings.UPLOAD_DIR)
