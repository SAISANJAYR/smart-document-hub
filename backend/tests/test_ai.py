"""Local (no-API-key) AI pipeline: language detection, deadline extraction, tagging, extractive answers."""

from datetime import datetime

import pytest

from app.core.agents.deadlines import extract_deadlines
from app.core.agents.tagger import local_tags
from app.core.ingestion.language import detect_language
from app.core.rag.engine import _extractive_answer

CIRCULAR = (
    "GOVERNMENT OF KERALA — FINANCE DEPARTMENT. Circular No. FIN/482/2026. "
    "All Heads of Departments must submit utilisation certificates on or before 15 December 2026 "
    "to the Finance Department through the BIMS portal. "
    "A review meeting will be held on 02/12/2026 at the Secretariat. "
    "Unspent balances must be remitted to the treasury."
)


def test_detects_malayalam_by_script():
    assert detect_language("കിറ്റ് വിതരണം എപ്പോൾ ആരംഭിക്കും?") == "ml"
    assert detect_language("When does the kit distribution begin?") == "en"


@pytest.mark.asyncio
async def test_deadlines_are_found_and_classified():
    events, _ = await extract_deadlines(CIRCULAR, base=datetime(2026, 11, 1))
    by_date = {e.event_date.date().isoformat(): e for e in events}
    assert by_date["2026-12-15"].event_type == "deadline"
    assert by_date["2026-12-02"].event_type == "meeting"
    assert "2026-12-15" not in by_date["2026-12-15"].event_title


def test_local_tagger_finds_type_and_department():
    r = local_tags(CIRCULAR)
    assert r.doc_type == "circular"
    assert r.department == "finance"
    assert not any(t in ("december", "november") for t in r.tags)


def test_extractive_answer_cites_its_source():
    passages = [{"text": CIRCULAR, "score": 0.7, "metadata": {}}]
    ans = _extractive_answer("When must utilisation certificates be submitted?", passages)
    assert "15 December 2026" in ans and "[1]" in ans


def test_extractive_answer_prefers_the_asked_for_fact():
    title = {"text": "Name of work: Resurfacing and drainage improvement of the Kaloor Road, Kochi. "
                     "Online bids are invited from registered contractors for the road tender.", "score": 0.44, "metadata": {}}
    emd = {"text": "Earnest Money Deposit (EMD) of Rs. 2,00,000 must be paid online on or before 27 November 2026.",
           "score": 0.41, "metadata": {}}
    ans = _extractive_answer("How much is the EMD for the road resurfacing tender?", [title, emd])
    assert ans.startswith("Earnest Money Deposit") and "Rs. 2,00,000" in ans
