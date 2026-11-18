"""
document.py — Beanie document models.

1. DocumentModel  — metadata + AI enrichment for every uploaded file
2. DateEvent      — extracted deadlines / milestones           (USP 1: Dynamic Calendar)
3. GraphEdge      — semantic links between two documents       (USP 2: Knowledge Graph)
4. QueryLog       — every question asked, with its trace       (history / audit)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, Field


class ProcessingStep(BaseModel):
    """One stage of the ingestion pipeline, recorded so the UI can show its working."""
    key: str
    label: str
    status: str = "done"  # done | skipped | failed
    ms: int = 0
    detail: Optional[str] = None


class Entity(BaseModel):
    text: str
    label: str  # ORG | PERSON | GPE | ...


class DocumentModel(Document):
    filename: str
    file_size: int
    mime_type: str
    file_hash: Indexed(str)  # type: ignore
    storage_path: str
    uploaded_by: Indexed(str)  # type: ignore
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Extraction
    page_count: Optional[int] = None
    char_count: int = 0
    chunk_count: int = 0
    text_preview: Optional[str] = None

    # Language (USP 4)
    language: Optional[str] = None
    translated: bool = False

    # AI enrichment (USP 3)
    detected_tags: List[str] = Field(default_factory=list)
    doc_type: Optional[str] = None
    department: Optional[str] = None
    summary: Optional[str] = None
    entities: List[Entity] = Field(default_factory=list)

    # Pipeline tracking
    processing_status: str = "pending"  # pending | processing | completed | failed
    processing_steps: List[ProcessingStep] = Field(default_factory=list)
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None

    class Settings:
        name = "documents"
        indexes = [
            [("detected_tags", pymongo.ASCENDING)],
            [("uploaded_by", pymongo.ASCENDING), ("uploaded_at", pymongo.DESCENDING)],
        ]


class DateEvent(Document):
    document_id: Indexed(str)  # type: ignore
    document_filename: str
    owner_id: Optional[str] = None
    event_date: Indexed(datetime)  # type: ignore
    event_title: str
    event_type: str = "date"  # deadline | meeting | payment | hearing | effective | expiry | date
    description: Optional[str] = None
    source_text: Optional[str] = None
    urgency: str = "medium"  # low | medium | high
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "date_events"


class GraphEdge(Document):
    source_doc_id: Indexed(str)  # type: ignore
    target_doc_id: Indexed(str)  # type: ignore
    weight: float = Field(..., ge=0.0, le=1.0)
    relation_type: str = "similarity"
    shared: List[str] = Field(default_factory=list)  # shared tags / entities
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "graph_edges"
        indexes = [[("source_doc_id", pymongo.ASCENDING), ("target_doc_id", pymongo.ASCENDING)]]


class QueryLog(Document):
    user_id: Indexed(str)  # type: ignore
    question: str
    answer: str
    question_language: str = "en"
    answer_language: str = "en"
    confidence: float = 0.0
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    engine: str = "extractive"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "query_logs"
