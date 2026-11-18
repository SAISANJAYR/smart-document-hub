"""
init_db.py — MongoDB + Beanie initialisation.

Tries the configured MongoDB first. If it is unreachable (or MONGODB_URL="mock://"),
falls back to an in-memory mongomock database so the app still runs for local demos.
"""

import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models.document import DateEvent, DocumentModel, GraphEdge, QueryLog
from app.models.user import User

logger = logging.getLogger(__name__)

DOCUMENT_MODELS = [User, DocumentModel, DateEvent, GraphEdge, QueryLog]

db_state = {"mode": "unknown"}


async def _init_mock():
    from mongomock_motor import AsyncMongoMockClient

    client = AsyncMongoMockClient()
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=DOCUMENT_MODELS)
    db_state["mode"] = "memory"
    logger.warning("[DB] Using in-memory MongoDB (mongomock). Data resets on restart.")


async def init_mongodb():
    if settings.MONGODB_URL.startswith("mock://"):
        await _init_mock()
        return

    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL, uuidRepresentation="standard", serverSelectionTimeoutMS=2500
        )
        await client.admin.command("ping")
        await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=DOCUMENT_MODELS)
        db_state["mode"] = "mongodb"
        logger.info("[DB] Connected to MongoDB at %s", settings.MONGODB_URL)
    except Exception as e:
        if not settings.MONGODB_FALLBACK_TO_MOCK:
            raise
        logger.warning("[DB] MongoDB unreachable (%s). Falling back to in-memory DB.", e)
        await _init_mock()
