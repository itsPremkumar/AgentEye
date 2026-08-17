# -*- coding: utf-8 -*-
"""AgentEye — Snippet quality scoring + query intent detection.

Pure text analysis. No APIs, no network calls.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Snippet quality scoring
# ---------------------------------------------------------------------------

# Definitive content signals (stronger than generic keywords)
DEFINITIVE_WORDS = {
    "how to", "what is", "guide", "tutorial", "documentation",
    "wiki", "definition", "explain", "vs", "comparison",
    "reference", "manual", "handbook", "textbook", "course",
    "introduction", "overview", "faq", "specs", "specification",
}


def snippet_quality_score(title: str, description: str, query: str) -> float:
    """Score how well a result snippet answers the query (0.0-1.0).

    Pure text analysis — keyword overlap, exact phrase match, and
    definitive-content signals. No APIs, no AI models.
    """
    query_words = set(re.findall(r'\b[a-z]{3,}\b', query.lower()))
    title_words = set(re.findall(r'\b[a-z]{3,}\b', title.lower()))
    desc_words = set(re.findall(r'\b[a-z]{3,}\b', description.lower()))

    if not query_words:
        return 0.5

    # Title match (strongest signal — title is what the page is about)
    title_overlap = len(query_words & title_words) / len(query_words)

    # Description match
    desc_overlap = len(query_words & desc_words) / len(query_words)

    # Bonus: query appears as exact phrase in title or description
    phrase_bonus = 0.0
    query_phrase = query.lower().strip()
    if query_phrase in title.lower():
        phrase_bonus = 0.3
    elif query_phrase in description.lower():
        phrase_bonus = 0.2

    # Penalty: snippet is empty or too short to be useful
    if len(description) < 20:
        return 0.1

    # Penalty: title is empty
    if len(title) < 5:
        return 0.2

    score = (title_overlap * 0.5) + (desc_overlap * 0.3) + phrase_bonus

    # Boost for "definitive" language (answers, guide, tutorial, wiki)
    if any(w in title.lower() for w in DEFINITIVE_WORDS):
        score += 0.1

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Query intent detection
# ---------------------------------------------------------------------------

INTENT_PATTERNS: dict[str, list[str]] = {
    "factual": [
        "what is", "who is", "when did", "where is", "why does",
        "how does", "define", "meaning", "wiki", "wikipedia",
        "origin", "history of", "biography",
    ],
    "how_to": [
        "how to", "how do i", "tutorial", "guide", "step by step",
        "learn", "example", "sample", "install", "setup", "configure",
    ],
    "news": [
        "latest", "news", "update", "today", "breaking", "recent",
        "announced", "released", "just", "happening", "trending",
    ],
    "comparison": [
        "vs", "versus", "difference", "better", "best",
        "compare", "or", "alternative", "like", "pros", "cons",
    ],
    "code": [
        "code", "example", "snippet", "function", "library", "api",
        "python", "javascript", "error", "bug", "fix", "github",
        "implementation", "algorithm", "syntax",
    ],
    "opinion": [
        "review", "opinion", "thoughts", "recommend", "should i",
        "worth it", "good", "bad", "best", "worst", "rating",
    ],
}


def detect_query_intent(query: str) -> dict[str, float]:
    """Return intent scores for a query (0.0-1.0 per intent).

    Pure keyword matching — no NLP models, no APIs.
    """
    query_lower = query.lower()
    intents: dict[str, float] = {}
    for intent, patterns in INTENT_PATTERNS.items():
        intents[intent] = sum(1.0 for p in patterns if p in query_lower)
    # Normalize so scores sum to ~1.0
    total = sum(intents.values())
    if total > 0:
        intents = {k: v / total for k, v in intents.items()}
    return intents


def dominant_intent(query: str) -> str:
    """Return the single highest-scoring intent."""
    intents = detect_query_intent(query)
    if not intents:
        return "factual"
    return max(intents, key=intents.get)


def intent_boost(title: str, description: str, intent: str) -> float:
    """Boost score if result matches detected intent (0.0-0.1)."""
    text = f"{title} {description}".lower()
    intent_signals: dict[str, list[str]] = {
        "factual": ["wiki", "definition", "what is", "encyclopedia", "britannica"],
        "how_to": ["tutorial", "guide", "how to", "step", "learn", "course"],
        "news": ["news", "reported", "announced", "today", "yesterday", "2026"],
        "comparison": ["vs", "difference", "comparison", "better", "pros", "cons"],
        "code": ["github", "code", "example", "snippet", "documentation", "api"],
        "opinion": ["review", "opinion", "rating", "verdict", "imho", "worth"],
    }
    signals = intent_signals.get(intent, [])
    return sum(0.1 for s in signals if s in text)
