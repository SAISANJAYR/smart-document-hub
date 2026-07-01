"""
documents.py — Documents and AI Query Router
-------------------------------------------
Contains endpoints for file uploads, document management, Q&A queries,
calendar deadlines, and knowledge graphs.
These are stubs for Day 2 to demonstrate Pydantic schema validation.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, status, Query
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

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="The PDF, DOCX, or Image file to upload"),
    custom_name: str | None = Form(None, description="Optional custom name override for the document")
):
    """
    Upload a document. The system will store the file and initiate
    the background ingestion, OCR, and chunking pipeline.
    """
    return DocumentResponse(
        id="doc_mock_999888",
        filename=custom_name or file.filename or "unknown.pdf",
        file_size=1024 * 350,  # 350 KB placeholder
        mime_type=file.content_type or "application/pdf",
        uploaded_by="user_mock_123456",
        uploaded_at=datetime.utcnow(),
        language="en",
        detected_tags=["mock", "stub", "upload"],
        processing_status="pending"
    )


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page")
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
            uploaded_by="user_mock_123456",
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
async def query_documents(payload: DocumentQueryRequest):
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
async def get_extracted_deadlines():
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
async def get_document_graph():
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
