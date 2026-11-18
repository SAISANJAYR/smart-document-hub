"""
nlp.py — Shared spaCy pipeline (loaded once, lazily) plus light text utilities.
"""

import logging
import re
from collections import Counter
from functools import lru_cache

logger = logging.getLogger(__name__)

STOPWORDS = set(
    """a about above after again against all also am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further had has have
    having he her here hers herself him himself his how i if in into is it its itself just me more most my
    myself no nor not now of off on once only or other our ours ourselves out over own same she should so some
    such than that the their theirs them themselves then there these they this those through to too under until
    up very was we were what when where which while who whom why will with would you your yours yourself
    yourselves shall may must per via etc ie eg i.e e.g within upon hereby therein thereof whereas said
    sir madam dear kindly please following above-mentioned page date dated ref no copy""".split()
)


CALENDAR_WORDS = set(
    """january february march april may june july august september october november december
    jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday
    saturday sunday today tomorrow year month week day am pm""".split()
)
SKIP_ENTS = {"DATE", "TIME", "CARDINAL", "ORDINAL", "MONEY", "PERCENT", "QUANTITY"}


@lru_cache(maxsize=1)
def get_nlp():
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        nlp.max_length = 2_000_000
        logger.info("spaCy en_core_web_sm loaded")
        return nlp
    except Exception as e:
        logger.warning("spaCy unavailable (%s); using regex fallbacks", e)
        return None


DOT = "․"  # one-dot leader, stands in for an abbreviation's period while splitting
SPLIT_RE = re.compile(r"(?<=[.!?।])\s+|\n{2,}|\n(?=[A-Z0-9•\-ഀ-ൿ])")
ABBREV_RE = re.compile(r"\b(Rs|No|Nos|Dr|Mr|Mrs|Ms|Smt|Sri|Shri|St|Rd|Ltd|Co|Dept|Govt|Sec|Vol|Fig|vs|approx|i\.e|e\.g|etc|w\.e\.f)\.\s", re.I)


def split_sentences(text: str) -> list[str]:
    # Protect abbreviations ("Rs. 2,00,000", "No. 12") so they don't end a sentence:
    # swap their dot for a placeholder, split, then restore it.
    text = ABBREV_RE.sub(lambda m: m.group(0)[:-2] + DOT + " ", text)
    parts = SPLIT_RE.split(text)
    return [re.sub(r"\s+", " ", p).replace(DOT, ".").strip() for p in parts if len(p.strip()) > 2]


def keywords(text: str, k: int = 6) -> list[str]:
    """Top noun-phrase keywords. Uses spaCy noun chunks when available, word frequency otherwise."""
    nlp = get_nlp()
    counts: Counter[str] = Counter()
    if nlp is not None:
        doc = nlp(text[:60000])
        for chunk in doc.noun_chunks:
            words = [
                (t.lemma_ if t.pos_ == "NOUN" else t.text).lower()
                for t in chunk
                if t.is_alpha and not t.is_stop and len(t) > 2
                and t.ent_type_ not in SKIP_ENTS and t.lower_ not in CALENDAR_WORDS
            ]
            if not words or len(words) > 3:
                continue
            phrase = " ".join(words)
            if phrase in STOPWORDS:
                continue
            counts[phrase] += 1 + (len(words) - 1) * 0.6
    else:
        for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
            if w not in STOPWORDS:
                counts[w] += 1

    picked: list[str] = []
    for phrase, _ in counts.most_common(k * 4):
        if any(phrase in p or p in phrase for p in picked):
            continue
        picked.append(phrase)
        if len(picked) >= k:
            break
    return picked


def lead_summary(text: str, max_sentences: int = 2, max_chars: int = 320) -> str:
    def is_body(s: str) -> bool:
        letters = [c for c in s if c.isalpha()]
        upper = sum(c.isupper() for c in letters) / (len(letters) or 1)
        # Skip letterheads and reference lines ("ROADS DIVISION … No. 77", "Subject: …").
        return len(s) > 40 and upper < 0.3 and ":" not in s[:40] and not re.search(r"\bNo\.\s*\S*\d", s)

    sents = [s for s in split_sentences(text) if is_body(s)]
    out = ""
    for s in sents[:max_sentences]:
        if len(out) + len(s) > max_chars and out:
            break
        out += (" " if out else "") + s
    return out[:max_chars].rstrip()
