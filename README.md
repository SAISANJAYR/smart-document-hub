# Smart Document Hub

**Ask your documents, in your language.** A multilingual document-intelligence platform: upload circulars, contracts and scanned notices in English or Malayalam, and it reads them, finds the deadlines, links related files, and answers questions with the exact passages it used.

Built for **Smart India Hackathon 2025** (PS SIH25080). This repository is the polished, end-to-end version of the hackathon prototype.

---

## What it does

| | Feature | How it works |
|---|---|---|
| 1 | **Dynamic calendar** | spaCy NER + regex find every date; `dateparser` normalises it; Gemini (or keyword rules) classifies it as deadline / payment / meeting / hearing / expiry / takes-effect and assigns urgency. Month view, agenda, `.ics` export. |
| 2 | **Knowledge graph** | Each document's centroid embedding (mean of its ChromaDB chunk vectors) is compared by cosine similarity with every other document; shared tags and entities nudge borderline pairs. Interactive force-directed view that explains *why* two files are linked. |
| 3 | **Tag-based search** | Tags (type, department, topics), a summary and named entities are generated on upload — Gemini with a Pydantic-validated JSON schema, or spaCy noun-chunks + rules offline. Search combines tag filters, semantic search and keyword matching, cached in Redis. |
| 4 | **Bilingual AI** | Malayalam is detected by Unicode script, translated to English for indexing, and questions asked in Malayalam are answered back in Malayalam — with both versions visible. The interface itself switches between English and മലയാളം. |

Every answer comes with a **visible trace** — language detection, translation, retrieval, generation, grounding check — each step timed, plus cited source passages. Every upload records what the pipeline did to it, step by step.

## Screens

Landing · Dashboard · Documents (upload, filters, tag cloud) · Document detail (text + translation, dates, entities, related files, pipeline trace) · **Ask** workspace (scope / question + answer / "How the system answered") · Search · Calendar · Knowledge graph · History.

## Architecture

```
React (Vite) ──► FastAPI ─┬─ Auth: JWT access + refresh, bcrypt, role checks, rate limiting
                          ├─ Ingestion pipeline (background task, per-step trace)
                          │    extract → detect language → translate → chunk + embed
                          │    → tags/summary/entities → deadlines → graph links
                          ├─ RAG engine: retrieve (ChromaDB) → Gemini / extractive answer → cite → translate back
                          └─ Storage: MongoDB (Beanie) · ChromaDB · Redis · /uploads
```

**Runs without any external service.** No Gemini key → spaCy rules and an IDF-weighted extractive answerer. No MongoDB → automatic fallback to an in-memory database. No Redis → in-process rate limits, no cache. Add the services and the same code uses them.

## Run it locally

Requirements: Python 3.12, Node 20+.

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm
cd backend
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

On first start the API seeds a demo account — **demo@dochub.dev / demo12345** — with seven sample district-office documents (DOCX, PDF, TXT, one in Malayalam) whose dates are relative to today, so the calendar is always live. Click **Try the demo account** on the landing page.

Optional: copy `.env.example` to `backend/.env` and set `GEMINI_API_KEY` for LLM-generated tags, date classification and answers.

## Run with Docker

```bash
cp .env.example .env              # add GEMINI_API_KEY if you have one
docker compose up --build         # http://localhost
```

Runs MongoDB, Redis, the API (with Tesseract + Malayalam for scans) and the frontend behind nginx.

## Tests

```bash
cd backend
pytest
```

Covers auth, upload validation and per-user isolation, Malayalam detection, deadline extraction and classification, local tagging, and the extractive answerer.

## Tech

**Backend** FastAPI · Pydantic v2 · Beanie / Motor · ChromaDB (all-MiniLM-L6-v2) · Google Gemini (`google-genai`) · spaCy · dateparser · langdetect · pdfplumber · python-docx · Tesseract / EasyOCR · Redis
**Frontend** React 19 · Vite · React Router · react-force-graph · Noto Serif / Noto Sans (+ Malayalam) type system
**Ops** Docker Compose · nginx

## API

Interactive docs at `/docs`. Main routes under `/api/v1`:

`POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` · `GET /auth/me`
`POST /documents/upload` · `GET /documents` · `GET /documents/{id}` · `GET /documents/{id}/text` · `GET /documents/{id}/file` · `PATCH /documents/{id}/tags` · `POST /documents/{id}/reprocess` · `DELETE /documents/{id}`
`POST /documents/query` · `GET /documents/queries` · `GET /documents/search` · `GET /documents/tags` · `GET /documents/calendar` · `GET /documents/graph` · `GET /documents/stats`
