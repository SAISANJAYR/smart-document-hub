"""
document.py — Document Pydantic Schemas
---------------------------------------
This file defines validation schemas for document upload metadata, Q&A queries,
citations, knowledge graphs, and extracted calendar events.

KEY CONCEPTS:
  1. Optional fields for metadata that gets populated in background tasks (e.g. tags, language).
  2. Nested schemas for complex structured responses (like graph nodes, citation sources, and calendar events).
"""

from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field


# ── Document Base & Response ─────────────────────────────────────────────────

class DocumentBase(BaseModel):
    filename: str = Field(..., description="Original name of the uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file (e.g., application/pdf)")


class DocumentResponse(DocumentBase):
    """
    Detailed response schema for a document.
    """
    id: str = Field(..., description="Unique database ID of the document")
    uploaded_by: str = Field(..., description="ID of the user who uploaded the document")
    uploaded_at: datetime = Field(..., description="Timestamp of when the document was uploaded")
    
    # AI/NLP extracted fields (may be null/empty initially during background tasks)
    language: str | None = Field(None, description="Detected dominant language (ISO 639-1 code)")
    detected_tags: List[str] = Field(default_factory=list, description="AI-extracted classification tags")
    processing_status: str = Field("pending", description="Status of the extraction pipeline (pending, processing, completed, failed)")
    error_message: str | None = Field(None, description="Pipeline error logs if processing failed")

    model_config = {
        "from_attributes": True
    }


class DocumentTagUpdate(BaseModel):
    """
    Request schema to manually override or add tags to a document.
    """
    tags: List[str] = Field(..., description="Complete list of tags for the document")


# ── RAG / Query Endpoints ───────────────────────────────────────────────────

class DocumentQueryRequest(BaseModel):
    """
    Request schema for querying a document or a set of documents.
    """
    question: str = Field(..., min_length=3, description="The query/question to ask the AI engine", examples=["What is the contract termination clause?"])
    document_ids: List[str] | None = Field(None, description="Optional list of document IDs to restrict search context. If empty, searches all documents user has access to.")


class CitationSource(BaseModel):
    """
    Source citation details indicating where the AI got its information.
    """
    document_id: str = Field(..., description="The ID of the source document")
    filename: str = Field(..., description="The name of the source document")
    page_number: int | None = Field(None, description="Page number of the citation if applicable")
    text_snippet: str = Field(..., description="A snippet of the matching text that was retrieved")
    similarity_score: float | None = Field(None, description="Vector search similarity score")


class DocumentQueryResponse(BaseModel):
    """
    Response schema returning the generated answer and source citations.
    """
    answer: str = Field(..., description="The generated response from the AI model")
    language: str = Field("en", description="The language of the response")
    citations: List[CitationSource] = Field(default_factory=list, description="List of source document citations used to generate the answer")


# ── USP 1: Extracted Deadlines / Calendar Events ──────────────────────────────

class DeadlineEventResponse(BaseModel):
    """
    Extracted calendar date event.
    """
    id: str = Field(..., description="Unique database ID of the calendar event")
    document_id: str = Field(..., description="ID of the document this deadline was extracted from")
    document_filename: str = Field(..., description="Filename of the source document")
    event_date: datetime = Field(..., description="The extracted deadline/milestone date")
    event_title: str = Field(..., description="A short summary of the event/actionable item")
    description: str | None = Field(None, description="Contextual description of the deadline")
    urgency: str = Field("medium", description="Urgency level (low, medium, high)")
    
    model_config = {
        "from_attributes": True
    }


# ── USP 2: Knowledge Graph ───────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node (usually the Document ID)")
    label: str = Field(..., description="Display label for the node (usually the Filename)")
    group: str = Field("document", description="Group category for styling nodes (e.g. document, tag)")


class GraphEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    weight: float = Field(..., description="Similarity weight between 0.0 and 1.0")
    relation_type: str = Field("similarity", description="The type of relationship (e.g. similarity, shared_tag)")


class KnowledgeGraphResponse(BaseModel):
    """
    Data structure representing the nodes and edges of the document network.
    """
    nodes: List[GraphNode] = Field(..., description="List of graph nodes")
    edges: List[GraphEdge] = Field(..., description="List of graph edges connecting the nodes")
