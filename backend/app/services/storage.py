import os
import shutil
import hashlib
from typing import Tuple
from fastapi import UploadFile
from app.config import settings

class LocalStorageService:
    """
    Handles saving uploaded files to the local disk.
    Later, this can be swapped with an S3StorageService.
    """
    
    def __init__(self, base_dir: str = "uploads"):
        # We store files relative to the project root
        self.base_dir = os.path.join(os.getcwd(), base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        
    async def save_file(self, file: UploadFile) -> Tuple[str, str]:
        """
        Reads the file, calculates its SHA-256 hash, and saves it to disk.
        Returns:
            Tuple containing: (file_path, file_hash)
        """
        # 1. Read file contents to compute hash
        content = await file.read()
        
        # 2. Compute SHA-256 hash (used to prevent duplicate uploads)
        file_hash = hashlib.sha256(content).hexdigest()
        
        # 3. Create a unique filename based on the hash
        # We append the original extension so the OS knows what type of file it is
        original_ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        safe_filename = f"{file_hash}{original_ext}"
        
        file_path = os.path.join(self.base_dir, safe_filename)
        
        # 4. Save to disk if it doesn't already exist
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(content)
                
        # 5. Reset the file cursor so other parts of the app (like OCR) can read it again if needed
        await file.seek(0)
        
        return file_path, file_hash

# Create a singleton instance we can use across the app
storage_service = LocalStorageService()
