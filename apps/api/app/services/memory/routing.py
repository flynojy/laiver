from app.utils.text import normalize_whitespace


MEMORY_ROUTE_HINTS = {
    "profile": (
        "prefer",
        "preference",
        "style",
        "tone",
        "what do i like",
        "what style",
        "how should you respond",
        "response style",
        "keep it practical",
    ),
    "instruction": (
        "remember",
        "always",
        "must",
        "should you",
        "do not",
        "don't",
        "rule",
        "instruction",
        "from now on",
    ),
    "episodic": (
        "last time",
        "earlier",
        "before",
        "yesterday",
        "today",
        "when we",
        "we discussed",
        "what happened",
        "previously",
    ),
}


def classify_memory_query(query: str) -> str:
    lowered = normalize_whitespace(query).lower()
    for route, markers in MEMORY_ROUTE_HINTS.items():
        if any(marker in lowered for marker in markers):
            return route
    return "general"
