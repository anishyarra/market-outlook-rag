# Report Intelligence (RAG) — Next.js + FastAPI

A “report intelligence” prototype:
- Upload PDFs → auto-index (page-aware chunks + metadata)
- Ask questions → answers grounded in retrieved excerpts
- Page citations + clickable sources that jump to the PDF viewer

---

## Repo structure

- `backend/` = FastAPI API + ingestion + retrieval (Chroma)
- `web/` = Next.js UI (App Router)

---

## Prerequisites

Install:
- Git
- Node.js 18+ (18 or 20 recommended)
- Python 3.11+ (3.11/3.12 recommended)

---

## Run locally (2 terminals)

### 1) Backend (FastAPI)

Open Terminal #1 in the repo root:

```bash
cd backend
python -m venv .venv
Activate venv:

Windows PowerShell

powershell
Copy code
.\.venv\Scripts\Activate.ps1
Mac/Linux

bash
Copy code
source .venv/bin/activate
Install Python deps:

bash
Copy code
pip install -r requirements.txt
Create backend/.env from the template (DO NOT COMMIT backend/.env):

Windows PowerShell

powershell
Copy code
Copy-Item .env.example .env
Mac/Linux

bash
Copy code
cp .env.example .env
Open backend/.env and set:

env
Copy code
OPENAI_API_KEY=YOUR_KEY_HERE
Run backend:

bash
Copy code
uvicorn app.main:app --reload --port 8000
Health check:

Open http://localhost:8000/whoami

Confirm it shows has_OPENAI_API_KEY: true

2) Frontend (Next.js)
Open Terminal #2 in the repo root:

bash
Copy code
cd web
npm install
Create web/.env.local (DO NOT COMMIT web/.env.local):

Windows PowerShell

powershell
Copy code
New-Item -Path .env.local -ItemType File
Put this inside web/.env.local:

env
Copy code
NEXT_PUBLIC_API_URL=http://localhost:8000
Run frontend:

bash
Copy code
npm run dev -- --port 3000
Open:

http://localhost:3000

How to use
Upload PDFs in the UI

Click a document in “Document library” to open it in the viewer

Click Generate Summary (summarizes the currently-viewed doc)

Toggle docs “Active/Off” to control which PDFs are used for retrieval

Ask questions and use “Open” in Sources to jump to cited pages