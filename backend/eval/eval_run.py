import csv
import json
import re
import argparse
from typing import List, Dict, Any, Optional

import requests


CITE_RE = re.compile(r"\(p\.\s*\d+\)", re.IGNORECASE)


def has_citations(text: str) -> bool:
    return bool(CITE_RE.search(text or ""))


def distinct_pages_from_sources(sources: List[Dict[str, Any]]) -> int:
    pages = set()
    for s in sources or []:
        md = (s.get("metadata") or {})
        p = md.get("page")
        did = md.get("doc_id")
        if p is not None and did is not None:
            pages.add((did, p))
    return len(pages)


def citation_coverage(answer: str) -> float:
    """
    Simple heuristic: fraction of non-empty lines that contain a (p.X).
    Not perfect, but good enough for comparing models quickly.
    """
    lines = [ln.strip() for ln in (answer or "").splitlines() if ln.strip()]
    if not lines:
        return 0.0
    cited = sum(1 for ln in lines if CITE_RE.search(ln))
    return cited / len(lines)


def get_docs(base_url: str) -> List[Dict[str, Any]]:
    r = requests.get(f"{base_url}/documents", timeout=30)
    r.raise_for_status()
    return r.json()


def ask(base_url: str, question: str, doc_ids: List[str], route: bool = True) -> Dict[str, Any]:
    payload = {"question": question, "doc_ids": doc_ids, "route": route}
    r = requests.post(f"{base_url}/chat", json=payload, timeout=180)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    ap.add_argument("--out", default="results.csv", help="Output CSV filename")
    ap.add_argument("--route", action="store_true", help="Enable router for eval questions")
    ap.add_argument("--doc-ids", default="", help="Comma-separated doc_ids to evaluate (blank = all docs)")
    ap.add_argument("--questions", default="", help="Path to questions.json (optional)")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")

    docs = get_docs(base_url)
    all_doc_ids = [d["doc_id"] for d in docs]

    if args.doc_ids.strip():
        doc_ids = [x.strip() for x in args.doc_ids.split(",") if x.strip()]
    else:
        doc_ids = all_doc_ids

    if not doc_ids:
        raise SystemExit("No docs found. Upload PDFs first, then rerun eval.")

    # Default eval set (edit as you want)
    questions = [
        "Summarize the report and list key themes.",
        "What does the report say about secondaries and liquidity?",
        "What does it say about private credit outlook for 2026?",
        "What are the biggest risks mentioned? Provide cited bullets.",
        "List any quantitative figures mentioned in the excerpts (with citations).",
        "Compare the two most different themes across the uploaded reports (with citations).",
        "What is missing or unclear in the report(s)? Provide analyst-style GAPS.",
        "Give 3 actionable takeaways for an LP allocator (with citations).",
    ]

    # Optional: load questions from a JSON file
    # Format: ["q1", "q2", ...]
    if args.questions:
        with open(args.questions, "r", encoding="utf-8") as f:
            questions = json.load(f)

    rows = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q}")
        res = ask(base_url, q, doc_ids=doc_ids, route=args.route)
        ans = res.get("answer", "")
        sources = res.get("sources", []) or []

        row = {
            "question": q,
            "route": args.route,
            "doc_ids_used": "|".join(doc_ids),
            "answer_has_citations": has_citations(ans),
            "citation_coverage": round(citation_coverage(ans), 3),
            "distinct_pages_cited": distinct_pages_from_sources(sources),
            "answer": ans,
        }
        rows.append(row)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "question",
                "route",
                "doc_ids_used",
                "answer_has_citations",
                "citation_coverage",
                "distinct_pages_cited",
                "answer",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {args.out} with {len(rows)} rows.")


if __name__ == "__main__":
    main()