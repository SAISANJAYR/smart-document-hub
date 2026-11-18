"""
documents.py — Documents, search, Q&A, calendar and knowledge-graph endpoints.
Every route is scoped to the authenticated user.
"""

import os
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.core.agents.llm import llm
from app.core.auth.dependencies import get_current_user
from app.core.graph.builder import remove_document_edges
from app.core.ingestion.pipeline import english_text_path, original_text_path, process_document
from app.core.rag.engine import answer_question
from app.core.rate_limit import RateLimit
from app.db.init_db import db_state
from app.models.document import DateEvent, DocumentModel, GraphEdge as GraphEdgeModel, QueryLog
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
    DeadlineEventResponse,
    DocumentDetailResponse,
    DocumentQueryRequest,
    DocumentQueryResponse,
    DocumentResponse,
    DocumentTagUpdate,
    DocumentTextResponse,
    GraphEdge,
    GraphNode,
    KnowledgeGraphResponse,
    QueryHistoryItem,
    RelatedDocument,
    SearchHit,
    SearchResponse,
    StatsResponse,
    TagCount,
)
from app.services.extractor import EXT_TO_MIME, SUPPORTED_MIME
from app.services.redis_cache import redis_service
from app.services.storage import storage_service
from app.services.vector_db import vector_db_service

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _user_docs(user: User, completed_only: bool = False) -> List[DocumentModel]:
    q = {"uploaded_by": str(user.id)}
    if completed_only:
        q["processing_status"] = "completed"
    return await DocumentModel.find(q).sort("-uploaded_at").to_list()


async def _get_owned(doc_id: str, user: User) -> DocumentModel:
    try:
        oid = PydanticObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = await DocumentModel.get(oid)
    if not doc or doc.uploaded_by != str(user.id):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _event_out(e: DateEvent) -> DeadlineEventResponse:
    return DeadlineEventResponse(
        id=str(e.id), document_id=e.document_id, document_filename=e.document_filename,
        event_date=e.event_date, event_title=e.event_title, event_type=e.event_type,
        description=e.description, urgency=e.urgency,
    )


# ── upload / list ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(RateLimit(times=30, seconds=60))])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, DOCX, TXT or image"),
    custom_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    mime = file.content_type if file.content_type in SUPPORTED_MIME else EXT_TO_MIME.get(ext)
    if mime not in SUPPORTED_MIME:
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload PDF, DOCX, TXT, PNG or JPG.")

    file_path, file_hash, size = await storage_service.save_file(file, max_bytes=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)

    existing = await DocumentModel.find_one({"file_hash": file_hash, "uploaded_by": str(current_user.id)})
    if existing:
        return existing

    doc = DocumentModel(
        filename=custom_name or file.filename or "document",
        file_size=size,
        mime_type=mime,
        file_hash=file_hash,
        storage_path=file_path,
        uploaded_by=str(current_user.id),
    )
    await doc.insert()
    background_tasks.add_task(process_document, doc.id)
    return doc


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Filter by filename"),
    tag: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    language: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    docs = await _user_docs(current_user)
    if q:
        docs = [d for d in docs if q.lower() in d.filename.lower()]
    if tag:
        docs = [d for d in docs if tag in d.detected_tags]
    if status_filter:
        docs = [d for d in docs if d.processing_status == status_filter]
    if language:
        docs = [d for d in docs if d.language == language]
    total = len(docs)
    start = (page - 1) * size
    return PaginatedResponse(items=docs[start : start + size], total=total, page=page, size=size,
                             pages=max(1, (total + size - 1) // size))


# ── dashboard ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def stats(current_user: User = Depends(get_current_user)):
    docs = await _user_docs(current_user)
    ids = [str(d.id) for d in docs]
    now = datetime.utcnow()
    events = await DateEvent.find({"document_id": {"$in": ids}, "event_date": {"$gte": now}}).to_list() if ids else []
    edges = await GraphEdgeModel.find({"source_doc_id": {"$in": ids}}).count() if ids else 0
    questions = await QueryLog.find(QueryLog.user_id == str(current_user.id)).count()
    langs = Counter(d.language for d in docs if d.language)
    tags = {t for d in docs for t in d.detected_tags}
    return StatsResponse(
        documents=len(docs),
        processed=sum(d.processing_status == "completed" for d in docs),
        processing=sum(d.processing_status in ("pending", "processing") for d in docs),
        failed=sum(d.processing_status == "failed" for d in docs),
        languages=dict(langs),
        upcoming_deadlines=len(events),
        high_urgency=sum(e.urgency == "high" for e in events),
        connections=edges,
        questions_asked=questions,
        tags=len(tags),
        engine={
            "llm": llm.model_name if llm.available else None,
            "database": db_state["mode"],
            "cache": "redis" if redis_service.redis_client else "off",
            "vector_db": "chromadb",
        },
    )


@router.get("/tags", response_model=List[TagCount])
async def list_tags(current_user: User = Depends(get_current_user)):
    counts = Counter(t for d in await _user_docs(current_user) for t in d.detected_tags)
    return [TagCount(tag=t, count=c) for t, c in counts.most_common()]


# ── search (USP 3) ───────────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query("", max_length=500),
    tags: Optional[str] = Query(None, description="Comma-separated tags; documents must have all of them"),
    top_k: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    t0 = time.perf_counter()
    tag_list = [t.strip().lower() for t in (tags or "").split(",") if t.strip()]
    cache_key = f"search:{current_user.id}:{q.lower()}:{','.join(sorted(tag_list))}:{top_k}"
    cached = await redis_service.get_cache(cache_key)
    if cached:
        cached["cached"] = True
        cached["took_ms"] = int((time.perf_counter() - t0) * 1000)
        return cached

    docs = await _user_docs(current_user, completed_only=True)
    if tag_list:
        docs = [d for d in docs if all(t in d.detected_tags for t in tag_list)]
    by_id: Dict[str, DocumentModel] = {str(d.id): d for d in docs}

    scores: Dict[str, float] = {}
    matched: Dict[str, set] = {}
    snippets: Dict[str, List[str]] = {}

    if q.strip():
        for hit in vector_db_service.search(q, n_results=top_k * 3, document_ids=list(by_id)):
            did = hit["metadata"].get("document_id")
            if did not in by_id:
                continue
            s = hit.get("score") or 0
            if s < 0.15:
                continue
            scores[did] = max(scores.get(did, 0), s)
            matched.setdefault(did, set()).add("semantic")
            if len(snippets.setdefault(did, [])) < 2:
                snippets[did].append(hit["text"][:280])
        ql = q.lower()
        for did, d in by_id.items():
            hay = " ".join([d.filename, d.summary or "", " ".join(d.detected_tags), d.doc_type or "", d.department or ""]).lower()
            if ql in hay or any(w in hay for w in ql.split() if len(w) > 3):
                scores[did] = scores.get(did, 0) + 0.15
                matched.setdefault(did, set()).add("keyword")
    else:
        for did in by_id:
            scores[did] = 1.0

    for did in scores:
        if tag_list:
            matched.setdefault(did, set()).add("tags")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    resp = SearchResponse(
        query=q,
        tags=tag_list,
        hits=[SearchHit(document=DocumentResponse.model_validate(by_id[did]), score=round(min(s, 1.0), 3),
                        matched_by=sorted(matched.get(did, [])), snippets=snippets.get(did, []))
              for did, s in ranked],
        took_ms=int((time.perf_counter() - t0) * 1000),
    )
    await redis_service.set_cache(cache_key, resp.model_dump(mode="json"), expire_seconds=300)
    return resp


# ── Q&A (RAG + USP 4) ────────────────────────────────────────────────────────

@router.post("/query", response_model=DocumentQueryResponse, dependencies=[Depends(RateLimit(times=20, seconds=60))])
async def query_documents(payload: DocumentQueryRequest, current_user: User = Depends(get_current_user)):
    docs = await _user_docs(current_user, completed_only=True)
    names = {str(d.id): d.filename for d in docs}
    ids = [i for i in (payload.document_ids or []) if i in names] or list(names)
    result = await answer_question(payload.question, ids, names, payload.answer_language)

    log = QueryLog(
        user_id=str(current_user.id), question=payload.question, answer=result["answer"],
        question_language=result["question_language"], answer_language=result["language"],
        confidence=result["confidence"], citations=result["citations"], trace=result["trace"], engine=result["engine"],
    )
    await log.insert()
    return DocumentQueryResponse(id=str(log.id), question=payload.question, created_at=log.created_at, **result)


@router.get("/queries", response_model=List[QueryHistoryItem])
async def query_history(limit: int = Query(50, ge=1, le=200), current_user: User = Depends(get_current_user)):
    logs = await QueryLog.find(QueryLog.user_id == str(current_user.id)).sort("-created_at").limit(limit).to_list()
    return [
        QueryHistoryItem(id=str(l.id), question=l.question, answer=l.answer, question_language=l.question_language,
                         answer_language=l.answer_language, confidence=l.confidence, engine=l.engine,
                         citations=l.citations, trace=l.trace, created_at=l.created_at)
        for l in logs
    ]


# ── Calendar (USP 1) ─────────────────────────────────────────────────────────

@router.get("/calendar", response_model=List[DeadlineEventResponse])
async def get_extracted_deadlines(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
):
    ids = [str(d.id) for d in await _user_docs(current_user)]
    if not ids:
        return []
    q: dict = {"document_id": {"$in": ids}}
    if start or end:
        q["event_date"] = {}
        if start:
            q["event_date"]["$gte"] = start
        if end:
            q["event_date"]["$lte"] = end
    events = await DateEvent.find(q).sort("event_date").to_list()
    return [_event_out(e) for e in events]


# ── Knowledge graph (USP 2) ──────────────────────────────────────────────────

@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_document_graph(
    include_entities: bool = False,
    min_weight: float = Query(0.0, ge=0, le=1),
    current_user: User = Depends(get_current_user),
):
    docs = await _user_docs(current_user, completed_only=True)
    ids = [str(d.id) for d in docs]
    if not ids:
        return KnowledgeGraphResponse(nodes=[], edges=[])

    edges_db = await GraphEdgeModel.find({"source_doc_id": {"$in": ids}, "target_doc_id": {"$in": ids}}).to_list()
    edges = [GraphEdge(source=e.source_doc_id, target=e.target_doc_id, weight=e.weight, relation_type=e.relation_type, shared=e.shared)
             for e in edges_db if e.weight >= min_weight]
    degree = Counter([e.source for e in edges] + [e.target for e in edges])
    nodes = [GraphNode(id=str(d.id), label=d.filename, group="document", doc_type=d.doc_type, language=d.language,
                       tags=d.detected_tags[:6], degree=degree[str(d.id)]) for d in docs]

    if include_entities:
        mentions: Dict[str, set] = {}
        labels: Dict[str, tuple] = {}
        for d in docs:
            for e in d.entities:
                key = e.text.lower()
                mentions.setdefault(key, set()).add(str(d.id))
                labels.setdefault(key, (e.text, e.label))
        for key, doc_ids in mentions.items():
            if len(doc_ids) < 2:
                continue
            text, label = labels[key]
            eid = f"entity:{key}"
            nodes.append(GraphNode(id=eid, label=text, group=label.lower(), degree=len(doc_ids)))
            for did in doc_ids:
                edges.append(GraphEdge(source=did, target=eid, weight=0.5, relation_type="mentions"))

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)


# ── single document ──────────────────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: str, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)
    events = await DateEvent.find(DateEvent.document_id == doc_id).sort("event_date").to_list()
    edges = await GraphEdgeModel.find({"$or": [{"source_doc_id": doc_id}, {"target_doc_id": doc_id}]}).to_list()
    other_ids = [e.target_doc_id if e.source_doc_id == doc_id else e.source_doc_id for e in edges]
    others = {str(d.id): d for d in await DocumentModel.find({"_id": {"$in": [PydanticObjectId(i) for i in other_ids]}}).to_list()} if other_ids else {}
    related = sorted(
        [RelatedDocument(id=oid, filename=others[oid].filename, weight=e.weight, shared=e.shared)
         for e, oid in zip(edges, other_ids) if oid in others],
        key=lambda r: r.weight, reverse=True,
    )
    data = DocumentResponse.model_validate(doc).model_dump()
    return DocumentDetailResponse(
        **data,
        text_preview=doc.text_preview,
        entities=[e.model_dump() for e in doc.entities],
        processing_steps=[s.model_dump() for s in doc.processing_steps],
        events=[_event_out(e) for e in events],
        related=related,
    )


@router.get("/{doc_id}/text", response_model=DocumentTextResponse)
async def get_document_text(doc_id: str, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)

    def read(p: str) -> Optional[str]:
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    original = read(original_text_path(doc.storage_path)) or ""
    english = read(english_text_path(doc.storage_path))
    return DocumentTextResponse(id=doc_id, language=doc.language, original=original,
                                english=english if english and english != original else None)


@router.get("/{doc_id}/file")
async def download_document(doc_id: str, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)
    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(doc.storage_path, media_type=doc.mime_type, filename=doc.filename)


@router.patch("/{doc_id}/tags", response_model=DocumentResponse)
async def update_tags(doc_id: str, payload: DocumentTagUpdate, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)
    clean = []
    for t in payload.tags:
        t = t.strip().lower()[:40]
        if t and t not in clean:
            clean.append(t)
    doc.detected_tags = clean
    await doc.save()
    await redis_service.delete_prefix(f"search:{current_user.id}:")
    return doc


@router.post("/{doc_id}/reprocess", response_model=DocumentResponse)
async def reprocess(doc_id: str, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)
    doc.processing_status = "pending"
    doc.processing_steps = []
    doc.error_message = None
    await doc.save()
    background_tasks.add_task(process_document, doc.id)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, current_user: User = Depends(get_current_user)):
    doc = await _get_owned(doc_id, current_user)
    vector_db_service.delete_document(doc_id)
    await DateEvent.find(DateEvent.document_id == doc_id).delete()
    await remove_document_edges(doc_id)
    # Only remove the file when no other document record points at it.
    if not await DocumentModel.find({"storage_path": doc.storage_path, "_id": {"$ne": doc.id}}).count():
        for p in (doc.storage_path, original_text_path(doc.storage_path), english_text_path(doc.storage_path)):
            try:
                os.remove(p)
            except OSError:
                pass
    await doc.delete()
    await redis_service.delete_prefix(f"search:{current_user.id}:")
