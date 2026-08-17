# -*- coding: utf-8 -*-
"""Agent Search Lite — Result summarization and interactive mode.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def summarize_results(
    results: List[Dict[str, Any]],
    query: str = "",
    max_sentences: int = 3,
    max_chars: int = 1000,
) -> str:
    """Generate an extractive summary of search results.
    
    This is LLM-free — it uses frequency-based sentence scoring.
    """
    if not results:
        return "No results to summarize."
    
    # Collect all text from results
    texts = []
    for r in results:
        parts = []
        if r.get("title"):
            parts.append(r["title"])
        if r.get("description"):
            parts.append(r["description"])
        if r.get("content"):
            parts.append(r["content"][:500])
        if parts:
            texts.append(" ".join(parts))
    
    combined = " ".join(texts)
    
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    
    # Simple sentence extraction
    sentences = _split_sentences(combined)
    
    if not sentences:
        return combined[:500] if combined else "No content available for summarization."
    
    # Score sentences by query term frequency
    if query:
        query_terms = set(query.lower().split())
        scored = []
        for sent in sentences:
            words = sent.lower().split()
            score = sum(1 for w in words if w in query_terms) / max(len(words), 1)
            scored.append((score, sent))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in scored[:max_sentences]]
    else:
        top_sentences = sentences[:max_sentences]
    
    # Restore original order
    ordered = [s for s in sentences if s in top_sentences]
    
    return " ".join(ordered)


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    import re
    
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out short sentences
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    return sentences[:20]


def format_interactive_prompt(query: str, mode: str) -> str:
    """Format the interactive mode prompt."""
    return f"agent-search [{mode}]> "


def print_welcome() -> None:
    """Print welcome message for interactive mode."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                   Agent Search Lite v3.0                    ║
║              Free Web Search for AI Agents                  ║
╠══════════════════════════════════════════════════════════════╣
║  Commands:                                                   ║
║    /help              - Show this help message              ║
║    /mode <mode>       - Switch mode (general/code/academic) ║
║    /limit <n>         - Set max results                     ║
║    /site <site>       - Filter to specific site             ║
║    /export <format>   - Export last results (json/csv/md)  ║
║    /history           - Show search history                ║
║    /doctor            - Check backend status               ║
║    /quit              - Exit interactive mode              ║
║                                                              ║
║  Query Operators:                                            ║
║    site:github.com     - Search GitHub only                 ║
║    after:2024-01-01    - Results after date                 ║
║    before:2025-01-01   - Results before date                ║
╚══════════════════════════════════════════════════════════════╝
""")
