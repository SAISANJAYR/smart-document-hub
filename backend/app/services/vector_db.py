"""
vector_db.py — ChromaDB wrapper: chunking, embedding, filtered semantic search and
per-document embedding centroids (used to build the knowledge graph).
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class VectorDBService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)

    def _ensure(self):
        if self.collection is not None:
            return True
        try:
            import chromadb

            path = settings.CHROMA_PATH
            if not os.path.isabs(path):
                path = os.path.join(BACKEND_ROOT, path)
            self.client = chromadb.PersistentClient(path=path)
            self.collection = self.client.get_or_create_collection(
                name="document_chunks", metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            logger.error("Failed to initialise ChromaDB: %s", e)
            return False

    @property
    def available(self) -> bool:
        return self._ensure()

    def add_document(self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        if not self._ensure():
            return 0
        chunks = self.splitter.split_text(text)
        if not chunks:
            return 0
        self.delete_document(document_id)
        metas, ids = [], []
        for i, _ in enumerate(chunks):
            meta = {k: v for k, v in (metadata or {}).items() if isinstance(v, (str, int, float, bool))}
            meta.update({"document_id": document_id, "chunk_index": i})
            metas.append(meta)
            ids.append(f"{document_id}_chunk_{i}")
        # Batch to keep memory flat on big documents.
        for start in range(0, len(chunks), 64):
            self.collection.add(
                documents=chunks[start : start + 64],
                metadatas=metas[start : start + 64],
                ids=ids[start : start + 64],
            )
        return len(chunks)

    def delete_document(self, document_id: str):
        if not self._ensure():
            return
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception as e:
            logger.warning("Chroma delete failed for %s: %s", document_id, e)

    def search(self, query: str, n_results: int = 5, document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if not self._ensure():
            return []
        if document_ids is not None and len(document_ids) == 0:
            return []
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}} if len(document_ids) > 1 else {"document_id": document_ids[0]}
        try:
            total = self.collection.count()
            if total == 0:
                return []
            res = self.collection.query(query_texts=[query], n_results=min(n_results, total), where=where)
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            return []
        out = []
        for i in range(len(res["documents"][0]) if res.get("documents") else 0):
            dist = res["distances"][0][i] if res.get("distances") else None
            out.append(
                {
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "distance": dist,
                    "score": round(max(0.0, 1.0 - dist), 4) if dist is not None else None,
                }
            )
        return out

    def document_centroid(self, document_id: str) -> Optional[np.ndarray]:
        if not self._ensure():
            return None
        try:
            got = self.collection.get(where={"document_id": document_id}, include=["embeddings"])
            embs = got.get("embeddings")
            if embs is None or len(embs) == 0:
                return None
            v = np.asarray(embs, dtype=np.float32).mean(axis=0)
            n = np.linalg.norm(v)
            return v / n if n else None
        except Exception as e:
            logger.warning("Centroid fetch failed for %s: %s", document_id, e)
            return None


vector_db_service = VectorDBService()
