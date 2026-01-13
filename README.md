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

## Run locally (2 terminals)

### 1) Backend (FastAPI)

#### Windows (PowerShell)

~~~powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env
# set OPENAI_API_KEY=YOUR_KEY_HERE inside the file, then save

uvicorn app.main:app --reload --port 8000
~~~

#### Mac/Linux

~~~bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
# set OPENAI_API_KEY=YOUR_KEY_HERE inside the file, then save

uvicorn app.main:app --reload --port 8000
~~~

**Backend health check:**  
Open: `http://localhost:8000/whoami`  
Confirm it shows `has_OPENAI_API_KEY: true`

---

### 2) Frontend (Next.js)

#### Windows (PowerShell)

~~~powershell
cd web
npm install

notepad .env.local
# put this inside:
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev -- --port 3000
~~~

#### Mac/Linux

~~~bash
cd web
npm install

echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev -- --port 3000
~~~

Open: `http://localhost:3000`

---

## How to use

1. Upload one or more PDFs in the UI.
2. Click a document in **Document library** to open it in the PDF viewer.
3. Click **Generate Summary** (summarizes the currently viewed document).
4. Toggle docs **Active / Off** to control which PDFs are included for retrieval.
5. Ask questions — use **Open** in Sources to jump to cited pages in the PDF viewer.

---

## Important: do NOT commit secrets

Never commit these files:

- `backend/.env`
- `web/.env.local`

If GitHub blocks your push because a key was committed:

1. Remove the key from the file(s)
2. Rotate the key in your OpenAI dashboard
3. Rewrite/amend commits so the key is not present in Git history

---

## Troubleshooting

### Upload fails (404)

- Confirm backend is running: `http://localhost:8000/whoami`
- Confirm `web/.env.local` contains:
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Restart both servers after changing env files.

### Upload fails (Failed to fetch)

- Backend not running, wrong API URL, or CORS issue
- Start backend first, then frontend
