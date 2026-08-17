# -*- coding: utf-8 -*-
"""AgentEye — Domain authority scoring (Google's PageRank principle, simplified).

Pure static lookup table. No APIs, no network calls.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Domain authority tiers — the closer to 1.0, the more trusted the source.
# Academic and government sites rank highest; social media and unknown rank
# lowest. This is a simplified version of Google's PageRank signal.
# ---------------------------------------------------------------------------

DOMAIN_AUTHORITY: dict[str, float] = {
    # Academic / Research (highest trust)
    "arxiv.org": 1.0,
    "pubmed.ncbi.nlm.nih.gov": 1.0,
    "nature.com": 1.0,
    "ieee.org": 1.0,
    "sciencedirect.com": 1.0,
    "springer.com": 0.95,
    "semanticscholar.org": 0.95,
    "crossref.org": 0.95,
    "openalex.org": 0.95,
    "doaj.org": 0.9,
    "plos.org": 0.9,
    "cell.com": 0.9,
    "thelancet.com": 0.9,
    "nejm.org": 0.9,
    "bmj.com": 0.9,
    "jamanetwork.com": 0.9,
    "pnas.org": 0.9,
    "acm.org": 0.9,
    "ucla.edu": 0.85,  # mirror/common prefix

    # News / Journalism
    "reuters.com": 0.95,
    "apnews.com": 0.95,
    "bbc.com": 0.95,
    "bbc.co.uk": 0.95,
    "nytimes.com": 0.9,
    "theguardian.com": 0.9,
    "npr.org": 0.9,
    "pbs.org": 0.9,
    "economist.com": 0.9,
    "wsj.com": 0.9,
    "washingtonpost.com": 0.9,
    "theatlantic.com": 0.85,
    "newyorker.com": 0.85,

    # Government / Official (high trust)
    "who.int": 0.95,
    "un.org": 0.9,
    "worldbank.org": 0.9,
    "imf.org": 0.9,
    "nasa.gov": 0.9,
    "nih.gov": 0.9,
    "cdc.gov": 0.9,
    "fda.gov": 0.9,
    "usgs.gov": 0.9,
    "noaa.gov": 0.9,
    "nist.gov": 0.9,
    "epa.gov": 0.9,
    "census.gov": 0.9,
    "bls.gov": 0.9,
    "treasury.gov": 0.9,
    "state.gov": 0.9,
    "europa.eu": 0.9,
    "oecd.org": 0.9,

    # Tech / Developer
    "github.com": 0.95,
    "gitlab.com": 0.9,
    "stackoverflow.com": 0.9,
    "stackexchange.com": 0.9,
    "news.ycombinator.com": 0.9,
    "dev.to": 0.8,
    "docs.python.org": 0.95,
    "docs.microsoft.com": 0.9,
    "learn.microsoft.com": 0.9,
    "developer.mozilla.org": 0.9,
    "developers.google.com": 0.9,
    "cloud.google.com": 0.9,
    "aws.amazon.com": 0.9,
    "azure.microsoft.com": 0.9,
    "oracle.com": 0.85,
    "redhat.com": 0.85,
    "ibm.com": 0.85,

    # Encyclopedic / Knowledge
    "wikipedia.org": 0.9,
    "wikidata.org": 0.85,
    "britannica.com": 0.9,
    "encyclopedia.com": 0.8,

    # Tech companies (official blogs/docs)
    "blog.google": 0.85,
    "ai.google": 0.9,
    "openai.com": 0.85,
    "anthropic.com": 0.85,
    "huggingface.co": 0.9,
    "pytorch.org": 0.9,
    "tensorflow.org": 0.9,
    "keras.io": 0.85,
    "scikit-learn.org": 0.9,
    "apache.org": 0.85,
    "kubernetes.io": 0.9,
    "docker.com": 0.85,

    # Social / Community (lower trust — user-generated content)
    "reddit.com": 0.6,
    "twitter.com": 0.5,
    "x.com": 0.5,
    "facebook.com": 0.4,
    "instagram.com": 0.4,
    "linkedin.com": 0.5,
    "tiktok.com": 0.3,
    "quora.com": 0.4,
    "pinterest.com": 0.3,

    # Known low-quality / spam farms (penalty)
    "medium.com": 0.5,  # mixed quality
}

# TLD-based authority (used when domain not found in list)
TLD_AUTHORITY: dict[str, float] = {
    "edu": 0.9,
    "gov": 0.95,
    "ac.uk": 0.9,
    "ac.jp": 0.9,
    "ac.in": 0.9,
    "org": 0.7,
    "int": 0.9,
    "com": 0.5,
    "net": 0.5,
    "io": 0.6,
    "co": 0.5,
    "info": 0.3,
    "biz": 0.3,
    "xyz": 0.2,
}


def domain_authority_score(url: str) -> float:
    """Return authority score 0.0-1.0 for a result URL.

    Uses exact domain match first, then parent domain, then TLD fallback.
    Unknown domains return 0.5 (neutral).
    """
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return 0.5
    # Strip www.
    if domain.startswith("www."):
        domain = domain[4:]

    # Exact match
    if domain in DOMAIN_AUTHORITY:
        return DOMAIN_AUTHORITY[domain]

    # Parent domain match (e.g., "blog.arxiv.org" → "arxiv.org")
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in DOMAIN_AUTHORITY:
            return DOMAIN_AUTHORITY[parent] * 0.95

    # TLD fallback
    tld = parts[-1] if parts else ""
    if tld in TLD_AUTHORITY:
        return TLD_AUTHORITY[tld]

    return 0.5  # unknown domain = neutral


def top_domain(url: str) -> str:
    """Extract the registrable domain (e.g., "blog.arxiv.org" → "arxiv.org")."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if domain.startswith("www."):
        domain = domain[4:]
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain
