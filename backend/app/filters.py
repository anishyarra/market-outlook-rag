import re

# Patterns that commonly show up in institutional PDF boilerplate / legal disclaimers
BOILERPLATE_PATTERNS = [
    r"\bdisclaimer\b",
    r"\bgeneral disclosure\b",
    r"\bimportant information\b",
    r"\bfor information purposes only\b",
    r"\bnot (?:intended|intended to be) (?:relied upon|a forecast)\b",
    r"\bnot investment advice\b",
    r"\bdoes not constitute investment advice\b",
    r"\bnot a recommendation\b",
    r"\boffer or solicitation\b",
    r"\bno representation (?:is|are) made\b",
    r"\bno (?:guarantee|assurance)\b",
    r"\bpast performance\b",
    r"\bcapital at risk\b",
    r"\bmay not get back\b",
    r"\bqualified investors?\b",
    r"\binstitutional\b",
    r"\bwholesale\b",
    r"\bprofessional(?:,)? qualified(?:,)? permitted\b",
    r"\bpermitted countr(y|ies)\b",
    r"\bsee the full disclaimer\b",
    # regulator / issuance boilerplate
    r"\bissued by\b",
    r"\bauthori[sz]ed and regulated\b",
    r"\bfinancial conduct authority\b",
    r"\bregistered office\b",
    r"\btelephone calls are usually recorded\b",
]

_WS = re.compile(r"\s+")
_NUM_TOKEN = re.compile(r"^-?\$?\d+([.,]\d+)?%?$")


def is_boilerplate(text: str) -> bool:
    """
    Return True if a chunk looks like boilerplate/disclaimer material.
    This is intentionally conservative: we only drop when it's strongly boilerplate.
    """
    t = (text or "").strip()
    if not t:
        return True

    lower = _WS.sub(" ", t.lower())

    # very short chunks are usually garbage
    if len(lower) < 80:
        return True

    hits = 0
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, lower):
            hits += 1

    # Strong signals → drop
    if hits >= 2:
        return True

    # Single strong phrase that is almost always legal boilerplate
    strong_phrases = [
        "for information purposes only",
        "does not constitute investment advice",
        "offer or solicitation",
        "authorised and regulated",
        "telephone calls are usually recorded",
        "financial conduct authority",
        "registered office",
        "general disclosure",
        "capital at risk",
        "past performance",
    ]
    if any(p in lower for p in strong_phrases):
        return True

    return False


def _numeric_ratio(text: str) -> float:
    toks = [t for t in re.split(r"\s+", (text or "").strip()) if t]
    if not toks:
        return 0.0
    numish = 0
    for t in toks:
        tt = t.strip("()[],:;")
        if _NUM_TOKEN.match(tt):
            numish += 1
    return numish / max(1, len(toks))


def looks_like_chart_or_table(text: str) -> bool:
    """
    Heuristic: chart/table dumps often have:
    - high numeric token ratio
    - many short, broken lines
    - axis-like content
    """
    t = (text or "").strip()
    if not t:
        return False

    # DO NOT auto-flag just because it's short (that killed real text).
    # Keep short stuff; your reranker can downweight it.
    if len(t) < 40:
        return False

    if _numeric_ratio(t) > 0.35:
        return True

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) >= 10:
        short = sum(1 for ln in lines if len(ln) <= 12)
        if short / len(lines) > 0.45:
            return True

    upper = t.upper()
    # navigation / repeated section headings
    if (
        upper.count("INTRODUCTION") >= 2
        and upper.count("PRIVATE CREDIT") >= 2
        and upper.count("PRIVATE EQUITY") >= 2
        and upper.count("REAL ESTATE") >= 2
    ):
        return True

    return False
