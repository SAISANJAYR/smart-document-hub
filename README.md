# 🧠 Smart Document Hub


A **production-grade multilingual document intelligence platform** built for SIH 2025 (PS ID: SIH25080).

---

## ✨ 4 Unique USPs

| # | Feature | Tech |
|---|---------|------|
| 1 | **Dynamic Calendar** — auto-extract dates/deadlines from every document | spaCy NER + Gemini + FullCalendar.js |
| 2 | **Document Graph** — interactive knowledge graph linking related docs | ChromaDB cosine similarity + D3.js |
| 3 | **Tag-Based Search** — AI-generated tags + semantic + keyword search | LangChain + MongoDB |
| 4 | **True Bilingual AI** — understands & responds in English + Malayalam | EasyOCR + IndicTrans2 + Gemini |

---

## 🏗️ Architecture

```
CLIENT (Next.js 14)
        ↓
API GATEWAY (FastAPI + JWT + CORS + Rate Limiting)
        ↓
CORE SERVICES (Ingestion · RAG · Calendar · Graph · Tags)
        ↓
AI LAYER (LangChain · LlamaIndex · spaCy · Gemini · EasyOCR)
        ↓
STORAGE (MongoDB · ChromaDB · Redis · /uploads)
```

---

## 🛠️ Tech Stack

**Backend**: FastAPI · Pydantic v2 · Motor · Beanie ODM  
**AI/RAG**: LangChain · LlamaIndex · ChromaDB · Google Gemini  
**NLP**: spaCy · EasyOCR · IndicTrans2 · langdetect  
**Frontend**: Next.js 14 · Tailwind CSS · shadcn/ui · D3.js · FullCalendar  
**DevOps**: Docker · Docker Compose · GitHub Actions · Nginx · Render  

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/yourusername/smart-document-hub.git
cd smart-document-hub

# 2. Setup Python environment
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r backend/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Run the API
cd backend
uvicorn app.main:app --reload

# 5. Open API docs
# http://localhost:8000/docs
```

---

## 📅 Build Progress

- [x] Week 1: Project scaffold + FastAPI basics
- [ ] Week 2: JWT Auth + User system
- [ ] Week 3: Document ingestion pipeline
- [ ] Week 4: ChromaDB + LlamaIndex RAG
- [ ] Week 5: LangChain + Tag system (USP 3)
- [ ] Week 6: Calendar (USP 1) + Document Graph (USP 2)
- [ ] Week 7: Next.js frontend
- [ ] Week 8: Bilingual AI (USP 4) + Admin
- [ ] Week 9: Testing + CI/CD + Cloud deploy
- [ ] Week 10: Polish + Portfolio

---


