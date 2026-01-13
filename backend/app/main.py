
# backend/app/main.py
import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .store import get_collection, get_paths
from .ingest import extract_pages, chunk_pages
from .rag import answer_question

from pathlib import Path
from dotenv import load_dotenv

import glob
from fastapi.responses import FileResponse

# Load .env from repo root (market-outlook-rag/market-outlook-rag/.env)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI(title="Market Outlook RAG (no-pdf)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatPayload(BaseModel):
    question: str
    doc_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    route: bool = True  # kept for compatibility (not used in single-doc mode)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stats")
def stats():
    col = get_collection()
    return {"chunks_indexed": col.count(), **get_paths()}

@app.get("/whoami")
def whoami():
    return {
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER"),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL"),
        "has_OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    paths = get_paths()
    doc_id = str(uuid.uuid4())

    safe_name = (file.filename or "document.pdf").replace("/", "_").replace("\\", "_")
    pdf_path = os.path.join(paths["docs_dir"], f"{doc_id}__{safe_name}")

    data = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(data)

    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)

    for c in chunks:
        c["metadata"]["doc_id"] = doc_id
        c["metadata"]["doc_name"] = safe_name

    col = get_collection()
    col.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    return {
        "status": "ok",
        "doc_id": doc_id,
        "doc_name": safe_name,
        "pages": len(pages),
        "chunks_added": len(chunks),
    }

@app.post("/chat")
async def chat(payload: ChatPayload):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")

    # Single-doc mode: accept doc_id OR doc_ids and pick one
    doc_id = payload.doc_id
    if (not doc_id) and payload.doc_ids:
        doc_id = payload.doc_ids[0]

    return answer_question(question, doc_id=doc_id)

@app.get("/debug-main")
def debug_main():
    return {"main_file": str(Path(__file__).resolve())}

@app.get("/pdf/{doc_id}")
def pdf(doc_id: str):
    docs_dir = get_paths()["docs_dir"]

    # files are saved like: {doc_id}__{safe_name}.pdf
    matches = glob.glob(os.path.join(docs_dir, f"{doc_id}__*.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="PDF not found for that doc_id")

    path = matches[0]
    filename = os.path.basename(path).split("__", 1)[-1]

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

@app.get("/routes")
def routes():
    return sorted([getattr(r, "path", str(r)) for r in app.router.routes])