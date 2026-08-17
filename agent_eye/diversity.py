# -*- coding: utf-8 -*-
"""AgentEye — Site diversity enforcement + content similarity deduplication.

Pure logic — no APIs, no AI models.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from agent_eye.domain_authority import top_domain


# ---------------------------------------------------------------------------
# Site diversity enforcement
# ---------------------------------------------------------------------------

def enforce_site_diversity(results: list, max_per_domain: int = 2) -> list:
    """Cap results per domain, then re-rank remaining.

    Google rarely shows more than 2 results from the same domain.
    We keep the top N per domain and push the rest to the bottom
    (still present, just deprioritized).
    """
    domain_counts: dict[str, int] = {}
    diverse: list = []
    remainder: list = []

    for r in results:
        domain = top_domain(r.get("url", ""))
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if domain_counts[domain] <= max_per_domain:
            diverse.append(r)
        else:
            remainder.append(r)

    # Append remainder at the bottom (still there, just deprioritized)
    return diverse + remainder


# ---------------------------------------------------------------------------
# Content similarity deduplication (fuzzy fingerprinting)
# ---------------------------------------------------------------------------

def _normalize_text(title: str, description: str) -> str:
    """Normalize text for fingerprinting — lowercase, alphanumeric, sorted."""
    words = re.findall(r'\b[a-z]{3,}\b', f"{title} {description}".lower())
    return " ".join(sorted(set(words)))


def content_fingerprint(title: str, description: str) -> str:
    """Create a fuzzy fingerprint for near-duplicate detection.

    Order-independent: "Python tutorial" and "tutorial Python" produce
    the same fingerprint.
    """
    normalized = _normalize_text(title, description)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def deduplicate_similar(results: list) -> list:
    """Remove near-duplicate results based on content fingerprinting.

    Two results with the same fingerprint (same set of significant words)
    are treated as duplicates. The first occurrence is kept.
    """
    seen_fingerprints: set = set()
    unique: list = []

    for r in results:
        fp = content_fingerprint(r.get("title", ""), r.get("description", ""))
        if fp not in seen_fingerprints:
            seen_fingerprints.add(fp)
            unique.append(r)

    return unique
