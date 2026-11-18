import os

# Tests never touch real services or seed demo data.
os.environ.setdefault("MONGODB_URL", "mock://")
os.environ.setdefault("SEED_DEMO", "false")
os.environ.setdefault("GEMINI_API_KEY", "")

import pytest_asyncio  # noqa: E402
from beanie import init_beanie  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

from app.core.rate_limit import reset_memory_limits  # noqa: E402
from app.db.init_db import DOCUMENT_MODELS  # noqa: E402


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_db():
    """Fresh in-memory MongoDB for every test."""
    client = AsyncMongoMockClient()
    await init_beanie(database=client.test_db, document_models=DOCUMENT_MODELS)
    reset_memory_limits()
    yield
