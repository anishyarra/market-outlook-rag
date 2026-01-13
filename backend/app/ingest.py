import re
import uuid
import math
from collections import Counter

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .filters import is_boilerplate, looks_like_chart_or_table


_WS = re.compile(r"\s+")
_DIGITS = re.compile(r"\d+")
_NONWORD = re.compile(r"[^\w\s]")


def extract_pages(pdf_path: str):
    """Return list of {page: int, text: str} with 1-indexed page numbers."""
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text") or ""
        pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def _norm_line(line: str) -> str:
    """
    Normalize line for repeated-line detection:
    - lowercase
    - collapse whitespace
    - remove digits/punctuation so footer variants still match
    """
    s = (line or "").strip().lower()
    s = _WS.sub(" ", s)
    s = _DIGITS.sub("", s)
    s = _NONWORD.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s


def build_repeated_line_blacklist(pages, min_frac: float = 0.35, min_pages: int = 3):
    """
    Find lines that repeat across many pages (headers/footers/disclaimer fragments).
    A line is considered boilerplate if it appears on >= max(min_pages, ceil(min_frac * n_pages)).
    """
    n_pages = max(1, len(pages))
    cutoff = max(min_pages, math.ceil(n_pages * min_frac))

    counts = Counter()
    for p in pages:
        seen = set()
        for raw in (p.get("text") or "").splitlines():
            norm = _norm_line(raw)
            if not norm:
                continue
            # Avoid nuking real headings that are very short
            if len(norm) < 10:
                continue
            seen.add(norm)
        counts.update(seen)

    return {line for line, c in counts.items() if c >= cutoff}


def strip_repeated_lines(text: str, blacklist: set[str]) -> str:
    """
    Remove:
      1) Lines whose normalized form matches repeated-line blacklist (headers/footers)
      2) Common institutional footer/header fragments (pattern-based)
    """
    out_lines = []
    for raw in (text or "").splitlines():
        line = (raw or "").strip()
        if not line:
            out_lines.append("")
            continue

        norm = _norm_line(line)
        upper = line.upper()

        # (A) Frequency-based removal with a safety guard
        if norm and norm in blacklist:
            # Only drop if it's header/footer-ish (short, all-caps, or very low alpha content)
            alpha = sum(ch.isalpha() for ch in line)
            if len(line) <= 80 or line.isupper() or alpha < 15:
                continue

        # (B) Pattern-based removal for common report footers/headers (general)
        if (
            "CAPITAL AT RISK" in upper
            or "FOR PUBLIC DISTRIBUTION" in upper
            or "FOR INSTITUTIONAL" in upper
            or "WHOLESALE" in upper
            or "QUALIFIED INVESTORS" in upper
            or "PERMITTED COUNTRIES" in upper
            or "SEE THE FULL DISCLAIMER" in upper
            or "PAST PERFORMANCE" in upper
            or "ILLUSTRATION PURPOSES ONLY" in upper
            or upper.startswith("EPMM")  # common document code footer
        ):
            continue

        # Generic “document code footer” like ABCD1234-12/34
        if re.fullmatch(r"[A-Z0-9/\-]{8,}", upper) and len(upper) <= 22:
            continue

        out_lines.append(raw.rstrip())

    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def chunk_pages(pages, chunk_size: int = 1800, chunk_overlap: int = 250):
    """
    Chunk each page separately so metadata keeps correct page numbers.
    Also strips repeated headers/footers prior to chunking.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    # Compute repeated-line blacklist once per document
    blacklist = build_repeated_line_blacklist(pages)

    chunks = []
    for p in pages:
        page_num = p["page"]

        # Strip repeated headers/footers BEFORE chunking
        page_text = strip_repeated_lines((p.get("text") or "").strip(), blacklist)
        if not page_text:
            continue

        for chunk in splitter.split_text(page_text):
            if is_boilerplate(chunk):
                continue
            if looks_like_chart_or_table(chunk):
                continue

            chunks.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": chunk,
                    "metadata": {"page": page_num},
                }
            )

    return chunks
