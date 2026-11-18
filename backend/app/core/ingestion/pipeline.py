"""
pipeline.py — The document ingestion pipeline.

    extract → detect language → translate (if Malayalam) → chunk + embed
            → AI tags → deadlines → link into knowledge graph

Every stage is timed and recorded on the document as a ProcessingStep, so the UI can
show exactly what the system did with each file.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from beanie import PydanticObjectId

from app.core.agents.deadlines import extract_deadlines
from app.core.agents.tagger import generate_tags
from app.core.graph.builder import link_document
from app.core.ingestion.language import LANG_NAMES, detect_language, translate
from app.models.document import DateEvent, DocumentModel, Entity, ProcessingStep
from app.services.extractor import extractor_service
from app.services.redis_cache import redis_service
from app.services.vector_db import vector_db_service

logger = logging.getLogger(__name__)

# Only one heavy pipeline at a time keeps CPU-bound NLP from starving the API.
_lock = asyncio.Semaphore(1)


class _Timer:
    def __init__(self):
        self.t = time.perf_counter()

    def ms(self) -> int:
        return int((time.perf_counter() - self.t) * 1000)


def english_text_path(storage_path: str) -> str:
    return storage_path + ".en.txt"


def original_text_path(storage_path: str) -> str:
    return storage_path + ".txt"


async def process_document(document_id: PydanticObjectId, base_date: Optional[datetime] = None):
    async with _lock:
        await _process(document_id, base_date)


async def _process(document_id: PydanticObjectId, base_date: Optional[datetime]):
    doc = await DocumentModel.get(document_id)
    if not doc:
        logger.error("Document %s not found", document_id)
        return

    steps: list[ProcessingStep] = []

    async def save_progress(status: str = "processing"):
        doc.processing_status = status
        doc.processing_steps = steps
        await doc.save()

    await save_progress()
    try:
        # 1 ── Extract
        t = _Timer()
        text, pages, method = await asyncio.to_thread(extractor_service.extract, doc.storage_path, doc.mime_type)
        text = (text or "").strip()
        if not text:
            raise ValueError("No readable text found in this file.")
        doc.page_count = pages
        doc.char_count = len(text)
        doc.text_preview = text[:600]
        with open(original_text_path(doc.storage_path), "w", encoding="utf-8") as f:
            f.write(text)
        steps.append(ProcessingStep(key="extract", label="Text extracted", ms=t.ms(),
                                    detail=f"{method} · {len(text):,} characters" + (f" · {pages} pages" if pages else "")))
        await save_progress()

        # 2 ── Language
        t = _Timer()
        lang = detect_language(text)
        doc.language = lang
        steps.append(ProcessingStep(key="language", label="Language detected", ms=t.ms(),
                                    detail=LANG_NAMES.get(lang, lang)))

        # 3 ── Translate to English for indexing
        english = text
        if lang != "en":
            t = _Timer()
            english, engine = await translate(text, lang, "en")
            doc.translated = engine not in (None, "none")
            steps.append(ProcessingStep(
                key="translate", label="Translated to English", ms=t.ms(),
                status="done" if doc.translated else "skipped",
                detail=f"via {engine}" if doc.translated else "translator unreachable; indexed original text",
            ))
        with open(english_text_path(doc.storage_path), "w", encoding="utf-8") as f:
            f.write(english)
        await save_progress()

        # 4 ── Chunk + embed
        t = _Timer()
        chunks = await asyncio.to_thread(
            vector_db_service.add_document,
            str(doc.id),
            english,
            {"filename": doc.filename, "language": lang, "owner_id": doc.uploaded_by},
        )
        doc.chunk_count = chunks
        steps.append(ProcessingStep(key="embed", label="Chunked and embedded", ms=t.ms(),
                                    status="done" if chunks else "failed",
                                    detail=f"{chunks} chunks · all-MiniLM-L6-v2 → ChromaDB"))
        await save_progress()

        # 5 ── Tags, summary, entities
        t = _Timer()
        tags, tag_engine = await generate_tags(english)
        doc.detected_tags = tags.tags
        doc.doc_type = tags.doc_type
        doc.department = tags.department
        doc.summary = tags.summary or None
        doc.entities = [Entity(text=e["text"], label=e.get("label", "ORG")) for e in tags.entities if e.get("text")]
        steps.append(ProcessingStep(key="tags", label="Tagged and summarised", ms=t.ms(),
                                    detail=f"{len(doc.detected_tags)} tags · {len(doc.entities)} entities · {tag_engine}"))
        await save_progress()

        # 6 ── Deadlines
        t = _Timer()
        await DateEvent.find(DateEvent.document_id == str(doc.id)).delete()
        events, dl_engine = await extract_deadlines(english, base=base_date or doc.uploaded_at)
        for e in events:
            await DateEvent(
                document_id=str(doc.id),
                document_filename=doc.filename,
                owner_id=doc.uploaded_by,
                event_date=e.event_date,
                event_title=e.event_title,
                event_type=e.event_type,
                description=e.source_text,
                source_text=e.source_text,
                urgency=e.urgency,
            ).insert()
        steps.append(ProcessingStep(key="deadlines", label="Dates and deadlines extracted", ms=t.ms(),
                                    detail=f"{len(events)} events · {dl_engine}"))
        await save_progress()

        # 7 ── Knowledge graph
        t = _Timer()
        doc.processing_status = "completed"  # so link_document sees a consistent state
        edges = await link_document(doc)
        steps.append(ProcessingStep(key="graph", label="Linked into knowledge graph", ms=t.ms(),
                                    detail=f"{edges} related documents · cosine similarity on embeddings"))

        doc.processed_at = datetime.utcnow()
        doc.error_message = None
        await save_progress("completed")
        await redis_service.delete_prefix(f"search:{doc.uploaded_by}:")
        logger.info("Processed %s (%s)", doc.filename, document_id)

    except Exception as e:
        logger.exception("Processing failed for %s", document_id)
        steps.append(ProcessingStep(key="error", label="Processing failed", status="failed", detail=str(e)[:300]))
        doc.error_message = str(e)[:500]
        await save_progress("failed")
