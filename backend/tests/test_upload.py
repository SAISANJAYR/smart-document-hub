import pytest
import pytest_asyncio
import os
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie, PydanticObjectId
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models.user import User
from app.models.document import DocumentModel
from app.core.auth.dependencies import get_current_user

# We use TestClient to make mock HTTP requests to our FastAPI app
client = TestClient(app)

# 1. Create a fake user that will bypass the JWT authentication
async def mock_get_current_user():
    return User(
        id=PydanticObjectId("60d5ec49f1b2c8b1f8e4e1a1"),
        email="test@example.com",
        full_name="Test User",
        hashed_password="mock_hash",
        role="viewer"
    )

# 2. Override the dependency in the FastAPI app
app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_db():
    """
    Initialize Beanie with a fake, in-memory MongoDB connection for documents.
    """
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client.test_db
    # We must init Beanie with ALL models used in the tests
    await init_beanie(database=mock_db, document_models=[User, DocumentModel])
    yield


@pytest.mark.asyncio
async def test_upload_document_success():
    """
    Test that uploading a file successfully saves metadata to DB.
    We mock the storage_service so it doesn't write real files to disk during tests.
    """
    # Create a small dummy file to upload
    file_content = b"Hello world, this is a mock PDF file."
    
    # We patch the storage service to return fake data so we don't pollute the hard drive
    with patch("app.api.v1.documents.storage_service.save_file", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = ("mock_uploads/dummy.pdf", "fakehash123")
        
        # TestClient handles sending multipart/form-data when you pass `files`
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("dummy.pdf", file_content, "application/pdf")},
            data={"custom_name": "Test Document"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["filename"] == "Test Document"
        assert data["processing_status"] == "pending"
        
        # Verify it was actually saved in the mock database
        doc_in_db = await DocumentModel.find_one(DocumentModel.file_hash == "fakehash123")
        assert doc_in_db is not None
        assert doc_in_db.filename == "Test Document"
        assert doc_in_db.storage_path == "mock_uploads/dummy.pdf"


@pytest.mark.asyncio
async def test_upload_document_duplicate():
    """
    Test that uploading a file with the exact same hash returns the existing document.
    """
    # 1. Insert an existing document into the mock DB
    existing_doc = DocumentModel(
        filename="original.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="duplicatehash123",
        storage_path="mock_uploads/original.pdf",
        uploaded_by="60d5ec49f1b2c8b1f8e4e1a1",
        processing_status="completed"
    )
    await existing_doc.insert()
    
    # 2. Try to upload a file that will generate the exact same hash
    file_content = b"Some duplicate content"
    
    with patch("app.api.v1.documents.storage_service.save_file", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = ("mock_uploads/new.pdf", "duplicatehash123")
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("new.pdf", file_content, "application/pdf")}
        )
        
        # It should return 201 but return the ORIGINAL document's metadata
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "original.pdf"
        assert data["processing_status"] == "completed"
