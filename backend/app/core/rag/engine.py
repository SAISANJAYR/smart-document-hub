"""
engine.py — Retrieval-augmented question answering with a visible trace.

    question → detect language → (translate to English) → retrieve passages from ChromaDB
             → generate a cited answer (Gemini, or extractive fallback) → grounding check
             → (translate answer back to Malayalam)

Every stage is timed and returned to the client, so users can see how an answer was made.
"""

import re
import time
from typing import Any, Dict, List, Optional

from app.core.agents.deadlines import DATE_RE
from app.core.agents.llm import llm
from app.core.agents.nlp import STOPWORDS, split_sentences
from app.core.ingestion.language import LANG_NAMES, detect_language, translate
from app.services.vector_db import vector_db_service

TOP_K = 6


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower())
    out = set()
    for w in words:
        if w in STOPWORDS or len(w) < 3:
            continue
        out.add(w.rstrip("s") if len(w) > 4 else w)
    return out


AMOUNT_RE = re.compile(r"(rs\.?|₹|inr|usd|\$)\s?[\d,]+|\b\d[\d,]*\s?(lakh|crore|percent|%)", re.I)
HEADER_RE = re.compile(r"^\s*(subject|sub|ref|reference|name of work|notification|circular no|e-tender notice|order no)\b", re.I)
QUESTION_WORDS = {"much", "many", "what", "when", "which", "who", "how", "does", "will", "need", "tell", "give", "list", "find"}


def _extractive_answer(question: str, passages: List[Dict[str, Any]]) -> str:
    """Picks the sentences that best cover the question, weighting rare terms (IDF) above common ones,
    so a decisive word like "EMD" beats words that appear in every passage like "tender"."""
    import math

    q = _terms(question) - QUESTION_WORDS
    sentences = []
    for idx, p in enumerate(passages):
        for pos, sent in enumerate(split_sentences(p["text"])):
            if len(sent) >= 25:
                sentences.append((idx, pos, sent, _terms(sent)))
    if not q or not sentences:
        return ""
    n = len(sentences)
    idf = {t: math.log(1 + n / (1 + sum(t in s[3] for s in sentences))) for t in q}
    total = sum(idf.values()) or 1

    # Expected answer type: boost sentences that contain the kind of thing being asked for.
    ql = question.lower()
    wants_amount = bool(re.search(r"how much|amount|fee|cost|price|emd|deposit|value|budget|salary|income", ql))
    wants_date = bool(re.search(r"\bwhen\b|date|deadline|by when|how long|till|until|ആരംഭ|തീയതി|എപ്പോൾ", ql))

    scored = []
    seen = set()
    for idx, pos, sent, terms in sentences:
        matched = q & terms
        if not matched or sent in seen:
            continue
        seen.add(sent)
        coverage = sum(idf[t] for t in matched) / total
        score = coverage + 0.3 * (passages[idx].get("score") or 0) - 0.005 * pos
        if HEADER_RE.match(sent):
            score -= 0.3  # "Subject: …", "Ref: …" restate the topic; they rarely answer anything
        if wants_amount and AMOUNT_RE.search(sent):
            score += 0.35
        if wants_date and DATE_RE.search(sent):
            score += 0.35
        scored.append((score, idx, pos, sent))
    if not scored:
        return ""
    scored.sort(reverse=True)
    top = scored[0][0]
    best = [r for r in scored[:3] if r[0] >= 0.85 * top]
    best.sort(key=lambda r: (r[1], r[2]))
    parts = []
    for _, idx, _, sent in best:
        sent = sent.rstrip()
        if not sent.endswith((".", "!", "?")):
            sent += "."
        parts.append(f"{sent} [{idx + 1}]")
    return " ".join(parts)


PROMPT = """You are a careful assistant answering questions about an organisation's documents.
Use ONLY the numbered sources below. Cite every claim with its source number like [1] or [2].
If the sources do not contain the answer, say so plainly. Be concise (at most 6 sentences).

Sources:
{sources}

Question: {question}
Answer:"""


class Trace:
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def add(self, key: str, label: str, t0: float, detail: str = "", status: str = "done", **extra):
        self.steps.append(
            {"key": key, "label": label, "status": status, "ms": int((time.perf_counter() - t0) * 1000), "detail": detail, **extra}
        )


async def answer_question(
    question: str,
    document_ids: List[str],
    filenames: Dict[str, str],
    answer_language: str = "auto",
) -> Dict[str, Any]:
    trace = Trace()

    # 1. Understand the question
    t = time.perf_counter()
    q_lang = detect_language(question)
    if q_lang not in ("en", "ml"):
        q_lang = "en"
    target_lang = q_lang if answer_language == "auto" else answer_language
    trace.add("question", "Question received", t, f"Language · {LANG_NAMES.get(q_lang, q_lang)}")

    # 2. Translate the question for retrieval
    q_en = question
    if q_lang != "en":
        t = time.perf_counter()
        q_en, engine = await translate(question, q_lang, "en")
        trace.add("translate_in", "Question translated", t,
                  f"“{q_en[:120]}” · via {engine}" if engine else "translator unreachable", status="done" if engine else "skipped")

    # 3. Retrieve
    t = time.perf_counter()
    passages = vector_db_service.search(q_en, n_results=TOP_K, document_ids=document_ids)
    doc_count = len({p["metadata"].get("document_id") for p in passages})
    top = max((p.get("score") or 0 for p in passages), default=0)
    trace.add("retrieve", "Passages retrieved", t,
              f"{len(passages)} passages from {doc_count} documents · best match {top:.2f}" if passages else "No matching passages",
              status="done" if passages else "failed")

    citations = [
        {
            "n": i + 1,
            "document_id": p["metadata"].get("document_id"),
            "filename": filenames.get(p["metadata"].get("document_id"), p["metadata"].get("filename", "document")),
            "chunk_index": p["metadata"].get("chunk_index"),
            "text_snippet": p["text"][:600],
            "similarity_score": p.get("score"),
        }
        for i, p in enumerate(passages)
    ]

    # 4. Generate
    t = time.perf_counter()
    engine = "extractive"
    answer_en: Optional[str] = None
    if passages and llm.available:
        sources = "\n\n".join(f"[{i + 1}] ({c['filename']})\n{p['text']}" for i, (p, c) in enumerate(zip(passages, citations)))
        answer_en = await llm.generate(PROMPT.format(sources=sources, question=q_en))
        if answer_en:
            engine = f"gemini ({llm.model_name})"
    if not answer_en and passages:
        answer_en = _extractive_answer(q_en, passages)
    if not answer_en:
        answer_en = "I couldn't find this in your documents. Try rephrasing, or upload the document that covers it."
    trace.add("generate", "Answer written", t,
              "Gemini, grounded on retrieved passages" if engine != "extractive" else "Extractive: best-matching sentences from the passages",
              engine=engine)

    # 5. Grounding / confidence
    t = time.perf_counter()
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer_en) if 0 < int(n) <= len(citations)}
    scores = sorted((p.get("score") or 0 for p in passages), reverse=True)[:3]
    retrieval = sum(scores) / len(scores) if scores else 0.0
    coverage = len(_terms(q_en) & _terms(answer_en)) / (len(_terms(q_en)) or 1)
    # Calibrated for all-MiniLM: strong matches score ~0.45–0.65 cosine, weak ones below ~0.25.
    confidence = round(min(0.99, 0.2 + 0.9 * retrieval + 0.25 * coverage) if passages and cited else (0.1 if passages else 0.0), 2)
    trace.add("check", "Claims checked", t,
              f"{len(cited)} of {len(citations)} sources cited · confidence {int(confidence * 100)}%")

    # 6. Translate back
    answer = answer_en
    if target_lang != "en":
        t = time.perf_counter()
        translated, tr_engine = await translate(answer_en, "en", target_lang)
        if tr_engine:
            answer = translated
        trace.add("translate_out", f"Answer translated to {LANG_NAMES.get(target_lang, target_lang)}", t,
                  f"via {tr_engine}" if tr_engine else "translator unreachable; showing English",
                  status="done" if tr_engine else "skipped")
        if not tr_engine:
            target_lang = "en"

    return {
        "answer": answer,
        "answer_en": answer_en,
        "language": target_lang,
        "question_language": q_lang,
        "question_en": q_en,
        "confidence": confidence,
        "engine": engine,
        "citations": [c for c in citations if c["n"] in cited] or citations[:3],
        "all_citations": citations,
        "trace": trace.steps,
    }
