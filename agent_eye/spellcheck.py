# -*- coding-8 -*-
"""AgentEye — Spell-check / typo detection + entity extraction.

Pure dictionary lookup + regex. No APIs, no AI models.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Spell-check: common search typos + corrections
# ---------------------------------------------------------------------------

COMMON_TYPOS: dict[str, str] = {
    # Programming languages
    "pyton": "python", "pytho": "python", "pyhton": "python",
    "pythn": "python", "pyton3": "python3",
    "javascrip": "javascript", "javscript": "javascript",
    "javascipt": "javascript", "javascrip": "javascript",
    "typscript": "typescript", "typescrip": "typescript",
    "javaascript": "javascript",
    # Platforms / Sites
    "guthub": "github", "gitub": "github", "gihub": "github",
    "stack overflow": "stackoverflow", "stakoverflow": "stackoverflow",
    "stackoverflw": "stackoverflow",
    "googlee": "google", "gooogle": "google",
    "reditt": "reddit", "redit": "reddit",
    "wkipedia": "wikipedia", "wikipdia": "wikipedia",
    # Tech terms
    "documenation": "documentation", "documantation": "documentation",
    "documention": "documentation",
    "artifical": "artificial", "artifcial": "artificial",
    "inteligence": "intelligence", "intellgence": "intelligence",
    "machien": "machine", "machin": "machine",
    "learing": "learning", "lerning": "learning",
    "neuralnetwork": "neural network",
    "deeplearning": "deep learning",
    "chatbot": "chatbot", "chat bot": "chatbot",
    # General
    "seach": "search", "serach": "search",
    "resutls": "results", "reuslts": "results",
    "progamming": "programming", "programing": "programming",
}


def suggest_correction(query: str) -> str | None:
    """Return corrected query if a known typo is found (None otherwise)."""
    query_lower = query.lower().strip()
    return COMMON_TYPOS.get(query_lower)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Edit distance between two strings (pure DP)."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            subs = prev[j] + (c1 != c2)
            curr.append(min(insertions, deletions, subs))
        prev = curr
    return prev[-1]


def is_typo(query: str, candidate: str, max_distance: int = 2) -> bool:
    """Return True if query is likely a typo of candidate."""
    return levenshtein_distance(query.lower(), candidate.lower()) <= max_distance


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

TECH_ENTITIES: set[str] = {
    "python", "javascript", "typescript", "rust", "go", "golang", "java",
    "c++", "c#", "swift", "kotlin", "scala", "r", "matlab", "ruby", "php",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "django",
    "flask", "fastapi", "spring", "rails", "express", "laravel",
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "terraform",
    "postgresql", "postgres", "mongodb", "mysql", "redis", "elasticsearch",
    "kafka", "rabbitmq", "nginx", "apache",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "transformers", "llama", "gpt", "bert", "diffusion",
    "linux", "ubuntu", "debian", "centos", "arch",
    "git", "github", "gitlab", "bitbucket",
    "vim", "neovim", "vscode", "jetbrains",
}


def extract_entities(query: str) -> dict:
    """Extract known entities from query.

    Pure keyword matching against a static tech entity list.
    No NLP models, no APIs.
    """
    words = set(re.findall(r'\b[a-z][a-z0-9+#.]*\b', query.lower()))
    return {
        "tech": list(words & TECH_ENTITIES),
        "question_words": [w for w in words if w in {
            "what", "how", "why", "when", "where", "who", "which"
        }],
        "has_year": bool(re.search(r"\b(20\d{2})\b", query)),
        "has_comparison": any(w in query.lower() for w in [
            "vs", "versus", "difference", "better", "or"
        ]),
    }
