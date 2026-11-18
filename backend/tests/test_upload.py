"""Upload endpoint: validation, de-duplication per user, and pipeline hand-off."""

from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from app.core.auth.dependencies import get_current_user
from app.main import app
from app.models.document import DocumentModel
from app.models.user import User

USER_ID = PydanticObjectId("60d5ec49f1b2c8b1f8e4e1a1")


async def fake_user():
    return User(id=USER_ID, email="test@example.com", full_name="Test User", hashed_password="x", role="viewer")


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


@pytest.mark.asyncio
async def test_upload_document_success():
    with patch("app.api.v1.documents.storage_service.save_file", new_callable=AsyncMock) as save, \
         patch("app.api.v1.documents.process_document", new_callable=AsyncMock) as process:
        save.return_value = ("mock_uploads/dummy.pdf", "fakehash123", 37)
        r = client.post(
            "/api/v1/documents/upload",
            files={"file": ("dummy.pdf", b"%PDF-1.4 mock", "application/pdf")},
            data={"custom_name": "Test Document"},
        )
    assert r.status_code == 201
    assert r.json()["filename"] == "Test Document"
    assert r.json()["processing_status"] == "pending"
    doc = await DocumentModel.find_one(DocumentModel.file_hash == "fakehash123")
    assert doc is not None and doc.file_size == 37
    process.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_duplicate_returns_existing():
    await DocumentModel(
        filename="original.pdf", file_size=1024, mime_type="application/pdf", file_hash="dup",
        storage_path="mock_uploads/original.pdf", uploaded_by=str(USER_ID), processing_status="completed",
    ).insert()
    with patch("app.api.v1.documents.storage_service.save_file", new_callable=AsyncMock) as save, \
         patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
        save.return_value = ("mock_uploads/new.pdf", "dup", 22)
        r = client.post("/api/v1/documents/upload", files={"file": ("new.pdf", b"x", "application/pdf")})
    assert r.status_code == 201
    assert r.json()["filename"] == "original.pdf"


@pytest.mark.asyncio
async def test_duplicate_of_another_users_file_is_not_shared():
    await DocumentModel(
        filename="theirs.pdf", file_size=1, mime_type="application/pdf", file_hash="same",
        storage_path="p", uploaded_by="someone-else",
    ).insert()
    with patch("app.api.v1.documents.storage_service.save_file", new_callable=AsyncMock) as save, \
         patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
        save.return_value = ("p", "same", 1)
        r = client.post("/api/v1/documents/upload", files={"file": ("mine.pdf", b"x", "application/pdf")})
    assert r.json()["filename"] == "mine.pdf"


def test_rejects_unsupported_type():
    r = client.post("/api/v1/documents/upload", files={"file": ("virus.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_other_users_document_is_404():
    doc = DocumentModel(filename="x", file_size=1, mime_type="text/plain", file_hash="h", storage_path="p", uploaded_by="other")
    await doc.insert()
    assert client.get(f"/api/v1/documents/{doc.id}").status_code == 404
