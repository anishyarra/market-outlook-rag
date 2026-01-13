# Report Intelligence (RAG) — Next.js + FastAPI

A lightweight “report intelligence” prototype:

- Upload PDFs → auto-index (page-aware chunks + metadata)
- Ask questions → grounded answers using retrieved excerpts (RAG)
- Page citations + clickable sources that jump to the PDF viewer

---

## Repo structure

- `backend/` — FastAPI API + ingestion + retrieval (Chroma)
- `web/` — Next.js UI (App Router)

---

## Prerequisites

Install:

- Git
- Node.js 18+ (18 or 20 recommended)
- Python 3.11+ (3.11/3.12 recommended)

---

## Quick start (Windows)

### Terminal #1 — Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env
# set OPENAI_API_KEY=YOUR_KEY_HERE inside the file, then save

uvicorn app.main:app --reload --port 8000

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
# set OPENAI_API_KEY=YOUR_KEY_HERE inside the file, then save

uvicorn app.main:app --reload --port 8000

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
# set OPENAI_API_KEY=YOUR_KEY_HERE inside the file, then save

uvicorn app.main:app --reload --port 8000


Open: http://localhost:3000