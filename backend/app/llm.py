# backend/app/llm.py
import os
import re
import json
from typing import List, Dict, Any, Optional
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

from openai import OpenAI


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _format_sources_for_prompt(
    sources: List[Dict[str, Any]],
    max_sources: int = 10,
    max_chars_per_source: int = 900,
) -> str:
    parts = []
    for s in sources[:max_sources]:
        meta = s.get("metadata", {}) or {}
        name = meta.get("doc_name", "report")
        page = meta.get("page", "?")
        text = _normalize_ws(s.get("text", ""))

        if len(text) > max_chars_per_source:
            text = text[:max_chars_per_source] + "…"

        parts.append(f"[{name} p.{page}] {text}")
    return "\n\n".join(parts)


# ---------------------------
# Providers
# ---------------------------

def _ollama_generate(prompt: str) -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))},
    }

    req = urlrequest.Request(
        url=f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTPError {e.code}. Response: {body[:500]}")
    except URLError as e:
        raise RuntimeError(f"Cannot reach Ollama at {host}. Is it running? Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")



def _openai_generate(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    history = history or []

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in backend/.env and restart backend.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()

    client = OpenAI(api_key=api_key, base_url=base_url)

    system = (
        "You are a careful investment/markets analyst. "
        "You must ONLY use the provided CONTEXT excerpts. "
        "You must cite page numbers exactly as (p.X). "
        "Never invent or guess page numbers."
    )

    # Build messages cleanly
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]

    # Include last N turns of history (keep small)
    for m in history[-8:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Final user prompt (your RAG prompt with CONTEXT)
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )

    return (resp.choices[0].message.content or "").strip()

def _mock_generate(question: str, sources: List[Dict[str, Any]]) -> str:
    top = sources[:5]
    bullets = []
    for s in top:
        p = (s.get("metadata", {}) or {}).get("page", "?")
        txt = _normalize_ws(s.get("text", ""))
        bullets.append(f"- {txt[:220]}… [p.{p}]")

    return (
        "Answer (MOCK): I’m grounding this response strictly in the retrieved report excerpts.\n\n"
        "Key points:\n"
        + "\n".join(bullets)
    )


# ---------------------------
# Main entry
# ---------------------------

def generate(question: str, context: str, sources: List[Dict[str, Any]], history: List[Dict[str, str]] | None = None) -> str:
    """
    LLM provider switch. Supported: MOCK, OLLAMA, OPENAI.
    """
    provider = os.getenv("LLM_PROVIDER", "MOCK").upper().strip()

    if provider == "MOCK":
        return _mock_generate(question, sources)

    src_block = _format_sources_for_prompt(
        sources,
        max_sources=int(os.getenv("MAX_SOURCES_FOR_LLM", "12")),
        max_chars_per_source=int(os.getenv("MAX_CHARS_PER_SOURCE", "900")),
    )

    prompt = f"""You are a careful analyst answering questions about a PDF report.
    Use ONLY the CONTEXT provided. Do not use outside knowledge.

    Hard rules:
    - For ANSWER / KEY THEMES / WHAT TO FOCUS ON IN 2026:
    - Every factual claim must include at least one citation like (p.7).
    - Do not invent page numbers.
    - If the context is insufficient for ANSWER, say exactly:
    "Not enough information in the provided excerpts."
    - For GAPS:
    - Do NOT use citations.
    - Do NOT say "Not enough information in the provided excerpts."
    - Write analyst-style gaps as a checklist: "Missing: <thing>. Look for: <what/where>."
    - GAPS should be 2–5 bullets.

    Output exactly these headers: ANSWER, KEY THEMES, WHAT TO FOCUS ON IN 2026, GAPS.

    Return EXACTLY this format:

    ANSWER:
    <2-6 sentences, each with citations OR the exact insufficient-info sentence>

    KEY THEMES:
    - <theme> (p.X)

    WHAT TO FOCUS ON IN 2026:
    - <actionable focus> (p.X)

    GAPS:
    - Missing: <thing>. Look for: <what/where to find it>.

    QUESTION:
    {question}

    CONTEXT:
    {src_block}
    """

    if provider == "OLLAMA":
        return _ollama_generate(prompt).replace("\r\n", "\n").strip()

    if provider == "OPENAI":
        return _openai_generate(prompt).replace("\r\n", "\n").strip()

    raise RuntimeError(f"Unknown LLM_PROVIDER={provider}. Use MOCK, OLLAMA, or OPENAI.")
