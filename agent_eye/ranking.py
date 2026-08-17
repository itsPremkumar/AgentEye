# -*- coding: utf-8 -*-
"""AgentEye — Result quality and ranking.

Pollution detection, cross-verification, token-conscious formatting,
domain authority, freshness, snippet quality, query intent, diversity,
and deduplication.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set

from agent_eye.domain_authority import domain_authority_score
from agent_eye.freshness import freshness_score, is_time_sensitive_query
from agent_eye.snippet_intent import (
    detect_query_intent,
    dominant_intent,
    intent_boost,
    snippet_quality_score,
)
from agent_eye.diversity import deduplicate_similar, enforce_site_diversity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pollution Detection
# ---------------------------------------------------------------------------

# Common spam/pollution indicators
POLLUTION_PATTERNS = [
    r"(?i)buy\s+now",
    r"(?i)\$\d+\.\d{2}",
    r"(?i)free\s+trial",
    r"(?i)limited\s+time\s+offer",
    r"(?i)click\s+here\s+to",
    r"(?i)subscribe\s+now",
    r"(?i)order\s+now",
    r"(?i)sign\s+up\s+free",
    r"(?i)discount\s+coupon",
    r"(?i)best\s+price\s+guarantee",
    r"(?i)no\s+credit\s+card\s+required",
    r"(?i)\d+%\s+off",
    r"(?i)sale\s+ends\s+(today|soon|now)",
    r"(?i)promo\s+code",
    r"(?i)free\s+shipping",
]

# High-quality content indicators
QUALITY_INDICATORS = [
    r"(?i)\d{4}",  # Year (recency)
    r"(?i)according\s+to",
    r"(?i)research\s+(shows|indicates|suggests)",
    r"(?i)study\s+(found|shows|indicates)",
    r"(?i)data\s+shows",
    r"(?i)analysis",
    r"(?i)documentation",
    r"(?i)guide",
    r"(?i)tutorial",
    r"(?i)introduction",
    r"(?i)overview",
    r"(?i)comparison",
    r"(?i)benchmark",
]


def is_polluted(title: str, description: str = "") -> bool:
    """Detect if a result is likely spam/pollution.

    Returns True if the result appears to be low-quality or spam.
    """
    text = f"{title} {description}".lower()

    pollution_score = sum(1 for p in POLLUTION_PATTERNS if re.search(p, text))

    # 2+ pollution patterns = likely spam
    return pollution_score >= 2


def quality_score(title: str, description: str = "") -> float:
    """Score result quality (0.0 to 1.0).

    Higher score = more likely to be high-quality, relevant content.
    """
    text = f"{title} {description}"

    # Base score
    score = 0.5

    # Boost for quality indicators
    quality_boosts = sum(1 for p in QUALITY_INDICATORS if re.search(p, text))
    score += quality_boosts * 0.05

    # Penalty for pollution
    pollution_penalties = sum(1 for p in POLLUTION_PATTERNS if re.search(p, text))
    score -= pollution_penalties * 0.15

    # Boost for reasonable length (not too short, not too long)
    title_len = len(title)
    if 20 <= title_len <= 100:
        score += 0.1

    desc_len = len(description)
    if 50 <= desc_len <= 500:
        score += 0.1

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Cross-Verification
# ---------------------------------------------------------------------------

def cross_verify(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cross-verify results from multiple sources.

    Adds verification metadata to each result:
    - verified_by: list of sources that corroborate
    - verification_score: 0.0 to 1.0
    """
    if not results:
        return results

    # Extract key terms from all results
    all_terms: Set[str] = set()
    for r in results:
        title = r.get("title", "").lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", title))
        all_terms.update(words)

    # For each result, count how many other results share key terms
    for r in results:
        title = r.get("title", "").lower()
        desc = r.get("description", "").lower()
        text = f"{title} {desc}"

        words = set(re.findall(r"\b[a-z]{3,}\b", text))
        shared = words & all_terms

        # Verification score based on term overlap
        if all_terms:
            r["verification_score"] = len(shared) / len(all_terms)
        else:
            r["verification_score"] = 0.0

        r["verified_by"] = []

    # Mark results as verified by source
    sources = set(r.get("source", "") for r in results)
    if len(sources) > 1:
        for r in results:
            r["verified_by"] = list(sources - {r.get("source", "")})

    return results


# ---------------------------------------------------------------------------
# Token-Conscious Result Formatting
# ---------------------------------------------------------------------------

def format_token_conscious(
    results: List[Dict[str, Any]],
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Format results to minimize token usage.

    Returns compact results with only essential fields.
    LLM can decide which pages to fetch in full.

    Approximate token counts:
    - title: ~1 token per 4 chars
    - URL: ~1 token per 10 chars
    - description: ~1 token per 4 chars

    Strategy: Return all titles+URLs first, then fill remaining budget with descriptions.
    """
    if not results:
        return {"results": [], "total_tokens": 0, "truncated": False}

    # Estimate tokens for each component
    def estimate_tokens(text: str) -> int:
        return len(text) // 4 + 1  # Rough estimate

    budget = max_tokens
    formatted = []
    total_tokens = 0

    # First pass: titles + URLs (always include)
    for r in results:
        title_tokens = estimate_tokens(r.get("title", ""))
        url_tokens = estimate_tokens(r.get("url", ""))
        cost = title_tokens + url_tokens + 3  # +3 for formatting

        if total_tokens + cost > budget:
            break

        formatted.append({
            "position": r.get("position", 0),
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": r.get("source", ""),
        })
        total_tokens += cost

    # Second pass: descriptions (fill remaining budget)
    remaining_budget = budget - total_tokens
    if remaining_budget > 50 and formatted:
        desc_budget = remaining_budget // len(formatted)

        for i, r in enumerate(formatted):
            original = results[i]
            desc = original.get("description", "")
            desc_tokens = estimate_tokens(desc)

            if desc_tokens <= desc_budget:
                formatted[i]["description"] = desc
                total_tokens += desc_tokens
            else:
                # Truncate description to fit budget
                max_chars = desc_budget * 4
                formatted[i]["description"] = desc[:max_chars] + "..."
                total_tokens += desc_budget

    return {
        "results": formatted,
        "total_tokens": total_tokens,
        "truncated": len(formatted) < len(results),
        "total_results": len(results),
    }


# ---------------------------------------------------------------------------
# Result Ranking (with all 8 improvements)
# ---------------------------------------------------------------------------

def rank_results(
    results: List[Dict[str, Any]],
    query: str = "",
) -> List[Dict[str, Any]]:
    """Rank results by quality, verification, relevance, domain authority,
    freshness, snippet quality, and query intent.

    Scoring factors:
    - Quality score (spam detection)
    - Verification score (cross-source corroboration)
    - Source priority (github > hackernews > reddit > jina-ddg)
    - Domain authority (arxiv.org > random-blog.blogspot.com)
    - Freshness (recent > old, weighted for time-sensitive queries)
    - Snippet quality (how well the snippet answers the query)
    - Query intent (boost results matching the query type)
    - Recency (if year in title/description)
    """
    if not results:
        return results

    source_priority = {
        "github": 1.0,
        "hackernews": 0.9,
        "reddit": 0.8,
        "jina-ddg": 0.7,
        "searxng": 0.85,
        "ddgs": 0.75,
    }

    query_lower = query.lower()
    query_words = set(re.findall(r"\b[a-z]{3,}\b", query_lower))

    # Detect query intent once for all results
    intent = dominant_intent(query)
    time_sensitive = is_time_sensitive_query(query)

    for r in results:
        score = 0.5

        # Source priority
        source = r.get("source", "")
        score *= source_priority.get(source, 0.5)

        # Quality score
        title = r.get("title", "")
        desc = r.get("description", "")
        qs = quality_score(title, desc)
        score += qs * 0.2

        # Verification score
        vs = r.get("verification_score", 0.0)
        score += vs * 0.15

        # Query relevance (word overlap)
        if query_words:
            result_words = set(re.findall(r"\b[a-z]{3,}\b", f"{title} {desc}".lower()))
            overlap = len(query_words & result_words) / len(query_words)
            score += overlap * 0.15

        # NEW: Domain authority (arxiv.org > random-blog.blogspot.com)
        da = domain_authority_score(r.get("url", ""))
        score += da * 0.2

        # NEW: Freshness (only for time-sensitive queries)
        if time_sensitive:
            fr = freshness_score(title, desc)
            score += fr * 0.15

        # NEW: Snippet quality (how well it answers the query)
        sn = snippet_quality_score(title, desc, query)
        score += sn * 0.1

        # NEW: Query intent boost (tutorials for how-to, news for latest)
        ib = intent_boost(title, desc, intent)
        score += ib

        # Pollution penalty
        if is_polluted(title, desc):
            score *= 0.3

        r["relevance_score"] = round(max(0.0, min(1.0, score)), 3)

    # Sort by relevance score (descending)
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    # NEW: Enforce site diversity (max 2 per domain)
    results = enforce_site_diversity(results, max_per_domain=2)

    # NEW: Deduplicate near-duplicate content
    results = deduplicate_similar(results)

    # Update positions after all re-ranking
    for i, r in enumerate(results):
        r["position"] = i + 1

    return results
