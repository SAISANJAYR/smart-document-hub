"""
document.py — Beanie Document Models
------------------------------------
Defines the MongoDB collection structures for the core entities:
1. Documents (metadata about uploaded files)
2. DateEvents (extracted deadlines for USP 1)
3. GraphEdges (document relationships for USP 2)
"""

from datetime import datetime
from typing import List, Optional
from beanie import Document, Indexed
from pydantic import Field
import pymongo


class DocumentModel(Document):
    """
    MongoDB document storing metadata about an uploaded file.
    Note: The actual file bytes are stored on disk/S3, and embeddings in ChromaDB.
    """
    filename: str = Field(..., description="Original name of the uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type (e.g., application/pdf)")
    
    file_hash: Indexed(str) = Field(..., description="SHA-256 hash to prevent duplicate uploads") # type: ignore
    storage_path: str = Field(..., description="Path where the physical file is stored")
    
    uploaded_by: Indexed(str) = Field(..., description="ID of the user who uploaded the document") # type: ignore
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # NLP & AI processing fields
    language: Optional[str] = Field(default=None, description="ISO 639-1 language code")
    detected_tags: List[str] = Field(default_factory=list, description="AI-extracted tags")
    
    # Pipeline tracking
    processing_status: str = Field(default="pending", description="pending, processing, completed, failed")
    error_message: Optional[str] = Field(default=None)

    class Settings:
        name = "documents"
        # We index tags heavily since we search by them often
        indexes = [
            [("detected_tags", pymongo.ASCENDING)]
        ]


class DateEvent(Document):
    """
    Extracted deadline or milestone event (USP 1: Calendar Integration)
    """
    document_id: Indexed(str) = Field(..., description="Source document ID") # type: ignore
    document_filename: str = Field(..., description="Cached filename for fast lookups")
    
    event_date: Indexed(datetime) = Field(..., description="The actual deadline date") # type: ignore
    event_title: str = Field(..., description="Short summary of the event")
    description: Optional[str] = Field(default=None)
    urgency: str = Field(default="medium", description="low, medium, high")
    
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "date_events"


class GraphEdge(Document):
    """
    Relationship link between two documents (USP 2: Knowledge Graph)
    """
    source_doc_id: Indexed(str) = Field(..., description="Source document ID") # type: ignore
    target_doc_id: Indexed(str) = Field(..., description="Target document ID") # type: ignore
    
    weight: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    relation_type: str = Field(default="similarity")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "graph_edges"
        indexes = [
            [("source_doc_id", pymongo.ASCENDING), ("target_doc_id", pymongo.ASCENDING)]
        ]
