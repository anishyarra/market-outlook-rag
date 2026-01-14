# backend/app/rag.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
import re

from .store import get_collection
from .llm import generate


def _cite_snippet(text: str, max_len: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    return (t[:max_len] + "…") if len(t) > max_len else t


def retrieve(
    query: str,
    k: int = 12,
    doc_id: Optional[str] = None,
    doc_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    col = get_collection()

    target_doc_ids = doc_ids or ([doc_id] if doc_id else None)

    def run_query(where_doc_id: Optional[str], n: int):
        kwargs = dict(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        if where_doc_id:
            kwargs["where"] = {"doc_id": where_doc_id}
        return col.query(**kwargs)

    out: List[Dict[str, Any]] = []

    if target_doc_ids:
        # Allocate retrieval budget fairly across docs
        # Example: if k=14 and 2 docs => ~7 per doc (plus buffer)
        per_doc = max(4, (k // len(target_doc_ids)) + 2)

        for did in target_doc_ids:
            res = run_query(did, per_doc)
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[None] * len(docs)])[0]

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
    else:
        # Global query across all docs
        n_raw = max(30, k * 4)
        res = run_query(None, n_raw)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[None] * len(docs)])[0]

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

    # Sort best-first (lower distance = closer)
    out.sort(key=lambda x: (x["distance"] if x["distance"] is not None else 999999))

    # Dedupe: 1 chunk per (doc_id, page) to increase page diversity
    seen = set()
    deduped = []
    for s in out:
        meta = s.get("metadata") or {}
        key = (meta.get("doc_id"), meta.get("page"))
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
    If the model forgets citations in ANSWER / KEY THEMES / WHAT TO FOCUS,
    replace those lines with the safe "Not enough information..." message.
    IMPORTANT: do NOT invent page numbers like (p.?).
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

        # Only enforce citations for the cite-required sections
        if needs_cite(line) and not cite_pattern.search(line):
            if section == "ANSWER":
                fixed.append("Not enough information in the provided excerpts.")
            else:
                fixed.append("- Not enough information in the provided excerpts.")
        else:
            fixed.append(line)

    return "\n".join(fixed)


def answer_question(
    question: str,
    doc_id: str | None = None,
    doc_ids: list[str] | None = None,
    route: bool = True,
    history: list[dict[str, str]] | None = None,  # Add history parameter
):
    sources = retrieve(question, k=14, doc_id=doc_id, doc_ids=doc_ids)
    context = format_context(sources)
    
    # Convert ChatMessage objects to dicts if needed
    history_dicts = None
    if history:
        history_dicts = [
            {"role": msg.get("role") if isinstance(msg, dict) else msg.role, 
             "content": msg.get("content") if isinstance(msg, dict) else msg.content}
            for msg in history
        ]
    
    answer = generate(question=question, context=context, sources=sources, history=history_dicts)
    answer = enforce_citations(answer)
    return {"answer": answer, "sources": sources}