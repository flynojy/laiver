from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "我",
    "我们",
    "你",
    "你们",
    "他",
    "她",
    "它",
    "的",
    "了",
    "是",
    "在",
    "和",
    "也",
    "要",
    "有",
    "一个",
}

CONCISE_HINTS = ("concise", "brief", "short", "summary first", "结论先行", "简洁", "精简")
DETAILED_HINTS = ("detailed", "context", "trade-off", "implementation notes", "long-form", "详细", "展开")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_whitespace(text).lower()
    return re.findall(r"[\u4e00-\u9fff]+|[a-z0-9']+", normalized)


def extract_keywords(texts: list[str], top_n: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(token for token in tokenize(text) if token not in STOPWORDS and len(token) > 1)
    return [token for token, _ in counter.most_common(top_n)]


def extract_phrases(texts: list[str], top_n: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = [token for token in tokenize(text) if token not in STOPWORDS]
        for size in (2, 3):
            for index in range(0, max(len(tokens) - size + 1, 0)):
                phrase = " ".join(tokens[index : index + size])
                if len(phrase) > 4:
                    counter[phrase] += 1
    return [phrase for phrase, count in counter.most_common(top_n) if count > 1]


def infer_tone(texts: list[str]) -> str:
    merged = " ".join(texts)
    lowered = merged.lower()
    if any(keyword in lowered for keyword in ("thanks", "thank you", "please")) or any(
        keyword in merged for keyword in ("谢谢", "感谢", "请")
    ):
        return "warm and collaborative"
    if any(keyword in lowered for keyword in ("must", "need to", "asap")) or any(
        keyword in merged for keyword in ("立刻", "马上", "必须")
    ):
        return "direct and action-oriented"
    if merged.count("?") > merged.count("!"):
        return "curious and reflective"
    return "clear and supportive"


def infer_verbosity(texts: list[str]) -> str:
    if not texts:
        return "balanced"
    joined = " ".join(texts).lower()
    if any(hint in joined for hint in CONCISE_HINTS):
        return "concise"
    if any(hint in joined for hint in DETAILED_HINTS):
        return "detailed"

    average_words = sum(len(tokenize(text)) for text in texts) / max(len(texts), 1)
    if average_words < 12:
        return "concise"
    if average_words < 24:
        return "balanced"
    return "detailed"


def infer_response_style(texts: list[str]) -> dict[str, object]:
    joined = " ".join(texts)
    return {
        "directness": "high" if ":" in joined or joined.count("\n") > 3 else "medium",
        "question_rate": round(joined.count("?") / max(len(texts), 1), 2),
        "emoji_usage": "low" if not re.search(r"[\U0001F300-\U0001FAFF]", joined) else "medium",
        "structure_preference": "structured" if joined.count("\n") > len(texts) else "paragraph",
    }


def infer_relationship_style(texts: list[str]) -> dict[str, object]:
    joined = " ".join(texts).lower()
    original = " ".join(texts)
    return {
        "warmth": "high"
        if any(word in joined for word in ("thanks", "appreciate", "please"))
        or any(word in original for word in ("谢谢", "感谢", "请"))
        else "medium",
        "formality": "medium",
        "collaboration": "high"
        if any(word in joined for word in ("we", "let's", "together"))
        or any(word in original for word in ("一起", "我们"))
        else "medium",
        "boundary_clarity": "high"
        if any(word in joined for word in ("must", "should", "prefer"))
        or any(word in original for word in ("不要", "必须", "偏好"))
        else "medium",
    }
