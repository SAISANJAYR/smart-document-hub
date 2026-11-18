"""
builder.py — Knowledge-graph construction (USP 2).

Each document is represented by the mean of its chunk embeddings (its centroid).
When a document finishes processing we compute cosine similarity against every other
document the same user owns and store an edge when they are semantically close or
share several tags/entities.
"""

import logging
from typing import List

import numpy as np

from app.config import settings
from app.models.document import DocumentModel, GraphEdge
from app.services.vector_db import vector_db_service

logger = logging.getLogger(__name__)


def _shared(a: DocumentModel, b: DocumentModel) -> List[str]:
    tags = set(a.detected_tags) & set(b.detected_tags)
    ents = {e.text.lower() for e in a.entities} & {e.text.lower() for e in b.entities}
    names = {e.text.lower(): e.text for e in a.entities}
    return sorted(tags) + sorted(names[e] for e in ents)


async def remove_document_edges(doc_id: str):
    await GraphEdge.find({"$or": [{"source_doc_id": doc_id}, {"target_doc_id": doc_id}]}).delete()


async def link_document(doc: DocumentModel) -> int:
    """Creates similarity edges between `doc` and the owner's other documents. Returns edge count."""
    await remove_document_edges(str(doc.id))
    me = vector_db_service.document_centroid(str(doc.id))
    others = await DocumentModel.find(
        {"uploaded_by": doc.uploaded_by, "processing_status": "completed", "_id": {"$ne": doc.id}}
    ).to_list()

    created = 0
    for other in others:
        shared = _shared(doc, other)
        sim = 0.0
        if me is not None:
            them = vector_db_service.document_centroid(str(other.id))
            if them is not None:
                sim = float(np.clip(np.dot(me, them), 0.0, 1.0))
        # Shared metadata nudges borderline pairs over the line.
        weight = min(1.0, sim + 0.04 * min(len(shared), 5))
        if weight >= settings.GRAPH_SIMILARITY_THRESHOLD or len(shared) >= 3:
            await GraphEdge(
                source_doc_id=str(doc.id),
                target_doc_id=str(other.id),
                weight=round(weight, 4),
                relation_type="similarity",
                shared=shared[:8],
            ).insert()
            created += 1
    return created
