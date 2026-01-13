# backend/app/rag.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
import re

from .store import get_collection
from .llm import generate


def _cite_snippet(text: str, max_len: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    return (t[:max_len] + "…") if len(t) > max_len else t


def retrieve(query: str, k: int = 12, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Basic vector retrieval from Chroma.
    - If doc_id is provided, filter to that document via where={"doc_id": doc_id}.
    - Pull extra results then truncate, to reduce junk.
    """
    col = get_collection()
    where = {"doc_id": doc_id} if doc_id else None

    n_raw = max(30, k * 4)

    kwargs = dict(
        query_texts=[query],
        n_results=n_raw,
        include=["documents", "metadatas", "distances"],
    )
    if where is not None:
        kwargs["where"] = where

    res = col.query(**kwargs)

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[None] * len(docs)])[0]

    out: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        text = (doc or "").strip()
        meta = meta or {}
        out.append(
            {
                "text": text,
                "snippet": _cite_snippet(text),
                "metadata": meta,
                "distance": dist,
            }
        )

    # Sort by distance (lower is better)
    out.sort(key=lambda x: (x["distance"] if x["distance"] is not None else 999999))

    # Page diversity: 1 chunk per page (simple)
    seen = set()
    deduped = []
    for s in out:
        page = (s.get("metadata") or {}).get("page")
        key = ((s.get("metadata") or {}).get("doc_id"), page)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
        if len(deduped) >= k:
            break

    return deduped


def format_context(sources: List[Dict[str, Any]]) -> str:
    parts = []
    for s in sources:
        meta = s.get("metadata", {}) or {}
        name = meta.get("doc_name", "report")
        page = meta.get("page", "?")
        text = (s.get("text") or "").replace("\n", " ").strip()
        parts.append(f"[{name} p.{page}] {text}")
    return "\n\n".join(parts)


def enforce_citations(output: str) -> str:
    """
    Lightweight enforcement: if model forgets citations, replace lines with a safe fallback.
    This prevents totally uncited answers from slipping through.
    """
    if not output:
        return output

    headers = {"ANSWER:", "KEY THEMES:", "WHAT TO FOCUS ON IN 2026:", "GAPS:"}
    cite_pattern = re.compile(r"\(p\.\s*\d+\)")

    lines = output.splitlines()
    fixed = []
    section = None

    def needs_cite(line: str) -> bool:
        if not line.strip():
            return False
        if line.strip() in headers:
            return False
        return section in {"ANSWER", "KEY THEMES", "WHAT TO FOCUS ON IN 2026"}

    for line in lines:
        stripped = line.strip()
        if stripped in headers:
            section = stripped[:-1]
            fixed.append(line)
            continue

        if needs_cite(line) and not cite_pattern.search(line):
            # safe fallback
            if section == "ANSWER":
                fixed.append("Not enough information in the provided excerpts. (p.?)")
            else:
                fixed.append("- Not enough information in the provided excerpts. (p.?)")
        else:
            fixed.append(line)

    return "\n".join(fixed)


def answer_question(question: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
    sources = retrieve(question, k=14, doc_id=doc_id)
    context = format_context(sources)
    answer = generate(question=question, context=context, sources=sources)
    answer = enforce_citations(answer)
    return {"answer": answer, "sources": sources}
