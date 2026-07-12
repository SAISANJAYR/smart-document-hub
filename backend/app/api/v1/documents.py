"""
documents.py — Documents and AI Query Router
-------------------------------------------
Contains endpoints for file uploads, document management, Q&A queries,
calendar deadlines, and knowledge graphs.
Now PROTECTED by JWT Authentication!
"""

import os
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, status, Query, Depends, BackgroundTasks
from app.schemas.document import (
    DocumentResponse, 
    DocumentQueryRequest, 
    DocumentQueryResponse,
    CitationSource,
    DeadlineEventResponse,
    KnowledgeGraphResponse,
    GraphNode,
    GraphEdge
)
from app.schemas.common import PaginatedResponse
from app.models.user import User
from app.models.document import DocumentModel
from app.core.auth.dependencies import get_current_user
from app.services.storage import storage_service
from app.services.extractor import extractor_service
from fastapi import HTTPException

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The PDF, DOCX, or Image file to upload"),
    custom_name: str | None = Form(None, description="Optional custom name override for the document"),
    current_user: User = Depends(get_current_user)  # 🔒 Protected Route
):
    """
    Upload a document. The system will store the file, prevent duplicates using hashes, 
    save metadata to MongoDB, and initiate the background processing pipeline.
    """
    # 1. Save the file to local storage and get its SHA-256 hash
    file_path, file_hash = await storage_service.save_file(file)
    
    # 2. Check if a document with this exact hash already exists to prevent duplicates!
    existing_doc = await DocumentModel.find_one(DocumentModel.file_hash == file_hash)
    if existing_doc:
        # If it exists, just return it instead of creating a new one
        return existing_doc
        
    # 3. Save new Document metadata to MongoDB
    filename = custom_name or file.filename or "unknown.bin"
    
    new_doc = DocumentModel(
        filename=filename,
        file_size=os.path.getsize(file_path),
        mime_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        storage_path=file_path,
        uploaded_by=str(current_user.id),
        processing_status="pending"
    )
    
    await new_doc.insert()
    
    # 4. Trigger the background task to extract text
    background_tasks.add_task(
        extractor_service.process_document_background,
        document_id=new_doc.id,
        file_path=file_path
    )
    
    return new_doc


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)  # 🔒 Protected Route
):
    """
    Retrieve a paginated list of all uploaded documents.
    """
    mock_items = [
        DocumentResponse(
            id="doc_mock_999888",
            filename="financial_report_2026.pdf",
            file_size=1024 * 350,
            mime_type="application/pdf",
            uploaded_by=str(current_user.id),
            uploaded_at=datetime.utcnow(),
            language="en",
            detected_tags=["finance", "report", "annual"],
            processing_status="completed"
        )
    ]
    return PaginatedResponse(
        items=mock_items,
        total=1,
        page=page,
        size=size,
        pages=1
    )


@router.post("/query", response_model=DocumentQueryResponse)
async def query_documents(
    payload: DocumentQueryRequest,
    current_user: User = Depends(get_current_user)  # 🔒 Protected Route
):
    """
    Query documents using the RAG search pipeline.
    """
    citation = CitationSource(
        document_id="doc_mock_999888",
        filename="financial_report_2026.pdf",
        page_number=4,
        text_snippet="Net revenue for Q3 2026 increased by 14% year-over-year to $4.2M.",
        similarity_score=0.92
    )
    
    return DocumentQueryResponse(
        answer=f"According to the documents, the financial metrics indicate: '{citation.text_snippet}'",
        language="en",
        citations=[citation]
    )


@router.get("/calendar", response_model=List[DeadlineEventResponse])
async def get_extracted_deadlines(
    current_user: User = Depends(get_current_user)  # 🔒 Protected Route
):
    """
    Retrieve extracted milestone and deadline events from the documents.
    """
    return [
        DeadlineEventResponse(
            id="evt_mock_555",
            document_id="doc_mock_999888",
            document_filename="financial_report_2026.pdf",
            event_date=datetime(2026, 12, 31, 23, 59, 59),
            event_title="FY2026 Annual Audit",
            description="Complete the compliance audit and report back to board members.",
            urgency="high"
        )
    ]


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_document_graph(
    current_user: User = Depends(get_current_user)  # 🔒 Protected Route
):
    """
    Retrieve the document relationship network (knowledge graph data).
    """
    return KnowledgeGraphResponse(
        nodes=[
            GraphNode(id="doc_mock_999888", label="financial_report_2026.pdf", group="document"),
            GraphNode(id="doc_mock_777777", label="tax_filings_2026.pdf", group="document")
        ],
        edges=[
            GraphEdge(source="doc_mock_999888", target="doc_mock_777777", weight=0.85, relation_type="similarity")
        ]
    )
