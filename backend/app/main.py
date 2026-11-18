"""
main.py — FastAPI application entry point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.agents.llm import llm
from app.db.init_db import db_state, init_mongodb
from app.services.redis_cache import redis_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)
    await init_mongodb()
    await redis_service.connect()

    if db_state["mode"] == "memory":
        # A fresh in-memory DB means every stored vector is orphaned; start clean.
        from app.services.vector_db import vector_db_service

        if vector_db_service.available:
            try:
                vector_db_service.client.delete_collection("document_chunks")
                vector_db_service.collection = None
            except Exception:
                pass

    seed_task = None
    if settings.SEED_DEMO:
        from app.seed import seed_demo

        seed_task = asyncio.create_task(seed_demo())

    # Warm spaCy in the background so the first upload isn't slow.
    from app.core.agents.nlp import get_nlp

    asyncio.get_running_loop().run_in_executor(None, get_nlp)

    yield

    if seed_task and not seed_task.done():
        seed_task.cancel()
    await redis_service.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    description="Multilingual document intelligence: RAG Q&A, deadline extraction, knowledge graph, AI tags.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"app": settings.APP_NAME, "version": app.version, "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "database": db_state["mode"],
        "cache": "redis" if redis_service.redis_client else "off",
        "llm": llm.model_name if llm.available else None,
    }


from app.api.v1 import router as api_v1_router  # noqa: E402

app.include_router(api_v1_router, prefix="/api/v1")
