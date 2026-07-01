"""
v1 API Router Assembly
-----------------------
Combines all sub-routers (auth, documents, etc.) under the /api/v1/ prefix.
"""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router

router = APIRouter()

# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(documents_router, prefix="/documents", tags=["Documents & RAG"])
