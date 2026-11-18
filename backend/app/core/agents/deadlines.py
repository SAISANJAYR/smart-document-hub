"""
deadlines.py — Deadline extraction (USP 1: Dynamic Calendar).

Hybrid pipeline:
  1. Detection   — spaCy NER finds DATE entities (regex fallback) and keeps their sentence.
  2. Parsing     — dateparser turns "15th December 2026" / "15/12/2026" into a datetime.
  3. Classifying — Gemini labels each (sentence, date) pair; locally, keyword rules do it.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.core.agents.llm import llm
from app.core.agents.nlp import get_nlp, split_sentences

logger = logging.getLogger(__name__)

MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_RE = re.compile(
    rf"\b(\d{{1,2}}(st|nd|rd|th)?[\s\-]+{MONTHS}[\s,\-]+\d{{4}}"
    rf"|{MONTHS}\s+\d{{1,2}}(st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{4}}"
    rf"|\d{{4}}-\d{{2}}-\d{{2}})\b",
    re.I,
)

TYPE_RULES = [
    ("deadline", ["last date", "deadline", "due date", "on or before", "not later than", "submit", "submission", "must be received", "closes on", "apply before"]),
    ("payment", ["payment", "pay ", "remit", "fee", "invoice", "instalment", "installment", "amount due"]),
    ("hearing", ["hearing", "court", "appear before", "tribunal"]),
    ("meeting", ["meeting", "conference", "review", "session", "workshop", "will be held", "convened", "training"]),
    ("expiry", ["expire", "expiry", "valid till", "valid until", "validity", "terminate", "renewal"]),
    ("effective", ["with effect from", "w.e.f", "effective from", "comes into force", "commence", "shall take effect"]),
]

TYPE_LABELS = {
    "deadline": "Deadline",
    "payment": "Payment due",
    "hearing": "Hearing",
    "meeting": "Meeting",
    "expiry": "Expiry",
    "effective": "Takes effect",
    "date": "Date",
}

BASE_URGENCY = {"deadline": "high", "payment": "high", "hearing": "high", "meeting": "medium", "expiry": "medium", "effective": "low", "date": "low"}


class ExtractedEvent(BaseModel):
    event_date: datetime
    event_type: str
    event_title: str
    urgency: str
    source_text: str
    date_text: str


def _parse_date(s: str, base: datetime) -> Optional[datetime]:
    import dateparser

    if not re.search(r"\d", s):
        return None
    if re.fullmatch(r"\s*\d{4}\s*", s):  # bare year
        return None
    if re.search(r"\b(days?|weeks?|months?|years?|hours?)\b", s, re.I) and not re.search(MONTHS, s, re.I):
        return None  # durations like "30 days"
    return dateparser.parse(
        s,
        settings={"DATE_ORDER": "DMY", "RELATIVE_BASE": base, "PREFER_DAY_OF_MONTH": "first", "REQUIRE_PARTS": ["month", "year"]},
    )


def _classify_local(sentence: str) -> str:
    low = sentence.lower()
    for etype, words in TYPE_RULES:
        if any(w in low for w in words):
            return etype
    return "date"


def _title(etype: str, sentence: str, date_text: str) -> str:
    clause = re.sub(
        r"(\b(on or before|not later than|on|by|before|from|till|until|dated?)\s+)?" + re.escape(date_text),
        " ", sentence, flags=re.I,
    ).strip()
    clause = re.sub(r"\s+", " ", clause)
    clause = re.sub(r"^(the|that|all|please note that|it is informed that)\s+", "", clause, flags=re.I)
    clause = re.sub(r"\b(on or before|not later than|before|by|on|from|till|until|dated?)\s*[,.]?\s*$", "", clause, flags=re.I).strip(" ,.;:-")
    if len(clause) > 80:
        clause = clause[:77].rsplit(" ", 1)[0] + "…"
    clause = clause[:1].upper() + clause[1:] if clause else ""
    return f"{TYPE_LABELS[etype]} · {clause}" if clause else TYPE_LABELS[etype]


def _urgency(etype: str, when: datetime, now: datetime) -> str:
    days = (when - now).days
    if days < 0:
        return "low"
    base = BASE_URGENCY.get(etype, "low")
    if days <= 7 and base != "low":
        return "high"
    if days > 60 and base == "high":
        return "medium"
    return base


def find_candidates(text: str, base: datetime) -> List[tuple[str, str, datetime]]:
    """(sentence, date_text, parsed_date) triples, deduplicated per (date, sentence)."""
    nlp = get_nlp()
    out: List[tuple[str, str, datetime]] = []
    seen = set()

    def add(sentence: str, date_text: str):
        when = _parse_date(date_text, base)
        if not when or not (1990 <= when.year <= 2100):
            return
        key = (when.date(), sentence[:60])
        if key in seen:
            return
        seen.add(key)
        out.append((sentence.strip(), date_text.strip(), when))

    if nlp is not None:
        doc = nlp(text[:150000])
        for ent in doc.ents:
            if ent.label_ == "DATE":
                add(re.sub(r"\s+", " ", ent.sent.text), ent.text)
    # Regex pass catches numeric formats spaCy often misses (15/12/2026).
    for sent in split_sentences(text):
        for m in DATE_RE.finditer(sent):
            add(sent, m.group(0))
    return out[:40]


CLASSIFY_PROMPT = """For each numbered sentence below, a date was found. Classify it.
Return a JSON list of objects: {{"i": int, "type": one of [deadline, payment, meeting, hearing, expiry, effective, date],
"title": a short action-oriented title (max 8 words, no date in it)}}.

{items}"""


async def extract_deadlines(text: str, base: Optional[datetime] = None) -> tuple[List[ExtractedEvent], str]:
    base = base or datetime.utcnow()
    now = datetime.utcnow()
    candidates = find_candidates(text, base)
    if not candidates:
        return [], "spaCy NER + dateparser"

    llm_labels: dict[int, dict] = {}
    engine = "spaCy NER + rules"
    if llm.available:
        items = "\n".join(f"{i}. [{d}] {s[:300]}" for i, (s, d, _) in enumerate(candidates))
        data = await llm.generate_json(CLASSIFY_PROMPT.format(items=items))
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict) and isinstance(row.get("i"), int):
                    llm_labels[row["i"]] = row
            engine = f"spaCy NER + gemini ({llm.model_name})"

    events: List[ExtractedEvent] = []
    for i, (sentence, date_text, when) in enumerate(candidates):
        label = llm_labels.get(i, {})
        etype = label.get("type") if label.get("type") in TYPE_LABELS else _classify_local(sentence)
        title = f"{TYPE_LABELS[etype]} · {label['title']}" if label.get("title") else _title(etype, sentence, date_text)
        events.append(
            ExtractedEvent(
                event_date=when,
                event_type=etype,
                event_title=title,
                urgency=_urgency(etype, when, now),
                source_text=sentence[:500],
                date_text=date_text,
            )
        )
    # Keep the most useful ones: typed events first, then plain dates.
    events.sort(key=lambda e: (e.event_type == "date", e.event_date))
    return events[:15], engine
