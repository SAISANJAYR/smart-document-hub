"""
init_db.py — Database Initialization
------------------------------------
Handles the connection to MongoDB using Motor and initializes Beanie ODM.

CONCEPT: Beanie needs to be "initialized" with the exact document classes
it will manage. This creates the collections and indexes in MongoDB.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.user import User
from app.models.document import DocumentModel, DateEvent, GraphEdge


async def init_mongodb():
    """
    Connect to MongoDB and initialize Beanie ODM with all models.
    This function will be called in the FastAPI lifespan event at startup.
    """
    print(f"[DB] Connecting to MongoDB at {settings.MONGODB_URL}...")
    
    # 1. Create a standard async Motor client
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        uuidRepresentation="standard"
    )
    
    # 2. Select the specific database name
    database = client[settings.MONGODB_DB_NAME]
    
    # 3. Initialize Beanie with our models
    await init_beanie(
        database=database,
        document_models=[
            User,
            DocumentModel,
            DateEvent,
            GraphEdge
        ]
    )
    
    print("[DB] Beanie ODM initialized successfully.")
