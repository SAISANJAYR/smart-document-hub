"""
document.py — API schemas for documents, Q&A, calendar events and the knowledge graph.
Kept separate from the Beanie models so internal fields (e.g. storage_path) never leak.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class ProcessingStepOut(BaseModel):
    key: str
    label: str
    status: str
    ms: int
    detail: Optional[str] = None


class EntityOut(BaseModel):
    text: str
    label: str


class DocumentResponse(BaseModel):
    id: PydanticObjectId
    filename: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime
    page_count: Optional[int] = None
    char_count: int = 0
    chunk_count: int = 0
    language: Optional[str] = None
    translated: bool = False
    detected_tags: List[str] = Field(default_factory=list)
    doc_type: Optional[str] = None
    department: Optional[str] = None
    summary: Optional[str] = None
    processing_status: str = "pending"
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeadlineEventResponse(BaseModel):
    id: str
    document_id: str
    document_filename: str
    event_date: datetime
    event_title: str
    event_type: str = "date"
    description: Optional[str] = None
    urgency: str = "medium"


class RelatedDocument(BaseModel):
    id: str
    filename: str
    weight: float
    shared: List[str] = Field(default_factory=list)


class DocumentDetailResponse(DocumentResponse):
    text_preview: Optional[str] = None
    entities: List[EntityOut] = Field(default_factory=list)
    processing_steps: List[ProcessingStepOut] = Field(default_factory=list)
    events: List[DeadlineEventResponse] = Field(default_factory=list)
    related: List[RelatedDocument] = Field(default_factory=list)


class DocumentTextResponse(BaseModel):
    id: str
    language: Optional[str]
    original: str
    english: Optional[str] = None


class DocumentTagUpdate(BaseModel):
    tags: List[str] = Field(..., max_length=20)


# ── Q&A ────────────────────────────────────────────────────────────────────

class DocumentQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, examples=["When is the last date to submit utilisation certificates?"])
    document_ids: Optional[List[str]] = Field(None, description="Restrict to these documents; empty = all of yours")
    answer_language: Literal["auto", "en", "ml"] = "auto"


class CitationSource(BaseModel):
    n: int
    document_id: str
    filename: str
    chunk_index: Optional[int] = None
    text_snippet: str
    similarity_score: Optional[float] = None


class TraceStep(BaseModel):
    key: str
    label: str
    status: str
    ms: int
    detail: str = ""
    engine: Optional[str] = None


class DocumentQueryResponse(BaseModel):
    id: Optional[str] = None
    question: str
    answer: str
    answer_en: str
    language: str
    question_language: str
    question_en: str
    confidence: float
    engine: str
    citations: List[CitationSource]
    all_citations: List[CitationSource]
    trace: List[TraceStep]
    created_at: Optional[datetime] = None


class QueryHistoryItem(BaseModel):
    id: str
    question: str
    answer: str
    question_language: str
    answer_language: str
    confidence: float
    engine: str
    citations: List[Dict[str, Any]]
    trace: List[Dict[str, Any]]
    created_at: datetime


# ── Search ──────────────────────────────────────────────────────────────────

class SearchHit(BaseModel):
    document: DocumentResponse
    score: float
    matched_by: List[str]
    snippets: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    tags: List[str]
    hits: List[SearchHit]
    took_ms: int
    cached: bool = False


class TagCount(BaseModel):
    tag: str
    count: int


# ── Graph ───────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    group: str = "document"
    doc_type: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    degree: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    relation_type: str = "similarity"
    shared: List[str] = Field(default_factory=list)


class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── Dashboard ───────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    documents: int
    processed: int
    processing: int
    failed: int
    languages: Dict[str, int]
    upcoming_deadlines: int
    high_urgency: int
    connections: int
    questions_asked: int
    tags: int
    engine: Dict[str, Any]
