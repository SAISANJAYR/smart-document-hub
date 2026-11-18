"""
tagger.py — AI tag generation (USP 3).

Gemini path: a structured prompt whose JSON reply is validated by a Pydantic model
(the "output parser" pattern). Local path: keyword rules for type/department,
spaCy noun-chunk keywords for topics and spaCy NER for entities.
"""

import logging
import re
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

from app.core.agents.llm import llm
from app.core.agents.nlp import get_nlp, keywords, lead_summary

logger = logging.getLogger(__name__)

DOC_TYPES = {
    "circular": ["circular"],
    "government order": ["government order", "g.o.", "g.o (", "go no", "it is hereby ordered", "sanction is accorded"],
    "notice": ["notice", "notification", "public notice"],
    "tender": ["tender", "bid", "rfp", "request for proposal", "quotation"],
    "contract": ["agreement", "contract", "hereinafter", "party of the first", "terms and conditions"],
    "invoice": ["invoice", "amount due", "bill to", "gst"],
    "minutes": ["minutes of the meeting", "minutes", "members present", "action taken"],
    "plan": ["action plan", "preparedness plan", "action points", "work plan"],
    "report": ["report", "findings", "executive summary", "analysis"],
    "policy": ["policy", "guidelines", "framework", "standard operating procedure"],
    "letter": ["dear sir", "dear madam", "yours faithfully", "yours sincerely"],
}

DEPARTMENTS = {
    "finance": ["budget", "finance", "expenditure", "fund", "accounts", "audit", "treasury", "payment"],
    "health": ["health", "hospital", "medical", "vaccination", "patient", "phc"],
    "education": ["school", "education", "student", "teacher", "university", "scholarship"],
    "revenue": ["revenue", "land", "tax", "village office", "taluk", "survey"],
    "public works": ["road", "bridge", "construction", "pwd", "infrastructure", "contractor"],
    "information technology": ["software", "it ", "digital", "e-governance", "server", "data"],
    "legal": ["court", "legal", "hearing", "petition", "act,", "section"],
    "human resources": ["leave", "recruitment", "promotion", "employee", "staff", "transfer"],
    "agriculture": ["agriculture", "farmer", "crop", "irrigation", "paddy"],
    "disaster management": ["flood", "disaster", "relief", "monsoon", "evacuation", "cyclone"],
    "environment": ["environment", "pollution", "forest", "waste", "climate"],
}


class TagResult(BaseModel):
    summary: str = ""
    doc_type: Optional[str] = None
    department: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    entities: List[dict] = Field(default_factory=list)

    @property
    def tags(self) -> List[str]:
        out: List[str] = []
        for t in [self.doc_type, self.department, *self.topics]:
            if t:
                t = t.strip().lower()
                if t and t not in out:
                    out.append(t)
        return out[:10]


def _score_map(text: str, table: dict[str, list[str]]) -> Optional[str]:
    low = text.lower()
    best, best_score = None, 0
    for label, words in table.items():
        score = sum(low.count(w) for w in words)
        if score > best_score:
            best, best_score = label, score
    return best


def extract_entities(text: str, limit: int = 25) -> List[dict]:
    nlp = get_nlp()
    if nlp is None:
        return []
    doc = nlp(text[:100000])
    seen: dict[str, dict] = {}
    for ent in doc.ents:
        if ent.label_ not in ("ORG", "PERSON", "GPE", "LAW"):
            continue
        name = re.sub(r"\s+", " ", ent.text).strip(" .,;:-\n")
        name = re.sub(r"^(the|a|an)\s+", "", name, flags=re.I)
        if len(name) < 3 or len(name) > 60 or name.lower() in ("the", "sir"):
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = {"text": name, "label": ent.label_}
        if len(seen) >= limit:
            break
    return list(seen.values())


def local_tags(text: str) -> TagResult:
    return TagResult(
        summary=lead_summary(text),
        doc_type=_score_map(text[:8000], DOC_TYPES),
        department=_score_map(text, DEPARTMENTS),
        topics=keywords(text, k=5),
        entities=extract_entities(text),
    )


PROMPT = """You are a records officer classifying an official document.
Return JSON with exactly these keys:
  "summary":    2 sentence plain-English summary,
  "doc_type":   one of {types},
  "department": the owning department in 1-3 lowercase words,
  "topics":     3-6 short lowercase topic tags (1-3 words each),
  "entities":   list of {{"text": str, "label": "ORG"|"PERSON"|"GPE"}} for key named entities (max 15).

Document:
\"\"\"{text}\"\"\""""


async def generate_tags(text: str) -> tuple[TagResult, str]:
    """Returns (result, engine)."""
    if llm.available:
        data = await llm.generate_json(PROMPT.format(types=", ".join(DOC_TYPES), text=text[:12000]))
        if data:
            try:
                result = TagResult.model_validate(data)
                if not result.entities:
                    result.entities = extract_entities(text)
                return result, f"gemini ({llm.model_name})"
            except ValidationError as e:
                logger.warning("Tag output failed validation, using local tagger: %s", e)
    return local_tags(text), "local (spaCy + rules)"
