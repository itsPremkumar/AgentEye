# -*- coding: utf-8 -*-
"""AgentLens — Quality Scoring, Citations, Multi-Language, Domain Profiles.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ===========================================================================
# Quality Scoring
# ===========================================================================

# Domain authority scores (higher = more authoritative)
DOMAIN_AUTHORITY = {
    # Academic
    "arxiv.org": 0.95,
    "pubmed.ncbi.nlm.nih.gov": 0.95,
    "nature.com": 0.93,
    "science.org": 0.93,
    "ieee.org": 0.90,
    "acm.org": 0.90,
    
    # Code
    "github.com": 0.95,
    "gitlab.com": 0.85,
    "stackoverflow.com": 0.90,
    "docs.python.org": 0.88,
    
    # Government
    "gov": 0.90,
    "data.gov": 0.90,
    "worldbank.org": 0.90,
    "un.org": 0.90,
    
    # News
    "bbc.com": 0.88,
    "reuters.com": 0.88,
    "nytimes.com": 0.85,
    "theguardian.com": 0.85,
    
    # Knowledge
    "wikipedia.org": 0.92,
    "wikidata.org": 0.88,
    
    # Tech News
    "news.ycombinator.com": 0.80,
    "techcrunch.com": 0.75,
    "theverge.com": 0.75,
}

# Source reliability scores
SOURCE_RELIABILITY = {
    "github": 0.95,
    "arxiv": 0.95,
    "pubmed": 0.95,
    "wikipedia": 0.90,
    "hackernews": 0.80,
    "reddit": 0.70,
    "stackoverflow": 0.85,
    "bbc": 0.88,
    "reuters": 0.88,
    "nasa": 0.95,
    "usgs": 0.95,
    "default": 0.60,
}


def quality_score(result: Dict[str, Any]) -> float:
    """Calculate quality score for a result (0.0 to 1.0)."""
    score = 0.0
    
    # Domain authority (30%)
    url = result.get("url", "")
    domain = urlparse(url).netloc.replace("www.", "")
    authority = 0.5  # default
    
    for domain_pattern, auth_score in DOMAIN_AUTHORITY.items():
        if domain.endswith(domain_pattern):
            authority = auth_score
            break
    
    score += authority * 0.30
    
    # Source reliability (25%)
    source = result.get("source", "default")
    reliability = SOURCE_RELIABILITY.get(source, SOURCE_RELIABILITY["default"])
    score += reliability * 0.25
    
    # Content completeness (20%)
    title = result.get("title", "")
    description = result.get("description", "")
    if title and len(title) > 10:
        score += 0.10
    if description and len(description) > 50:
        score += 0.10
    
    # Freshness (15%)
    timestamp = result.get("timestamp") or result.get("date") or result.get("created")
    if timestamp:
        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                age_hours = (datetime.now().timestamp() - timestamp) / 3600
            elif isinstance(timestamp, str):
                # ISO format
                from dateutil.parser import parse
                age_hours = (datetime.now() - parse(timestamp)).total_seconds() / 3600
            else:
                age_hours = 24
            
            if age_hours < 1:
                score += 0.15
            elif age_hours < 24:
                score += 0.10
            elif age_hours < 168:  # 1 week
                score += 0.05
            else:
                score += 0.02
        except Exception:
            pass
    
    # Structured data bonus (10%)
    if result.get("json_ld") or result.get("open_graph"):
        score += 0.10
    
    return min(score, 1.0)


def rank_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank results by quality score."""
    for result in results:
        result["quality_score"] = quality_score(result)
    
    results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    return results


# ===========================================================================
# Source Citations
# ===========================================================================

def generate_citation(result: Dict[str, Any]) -> Dict[str, str]:
    """Generate a citation for a result."""
    return {
        "title": result.get("title", "Untitled"),
        "url": result.get("url", ""),
        "source": result.get("source", "Unknown"),
        "accessed_at": datetime.now().isoformat(),
        "published_at": result.get("date") or result.get("timestamp") or result.get("created", ""),
        "confidence": f"{result.get('quality_score', 0) * 100:.0f}%",
    }


def generate_citations(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate citations for multiple results."""
    return [generate_citation(r) for r in results]


# ===========================================================================
# Multi-Language Support
# ===========================================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "bn": "Bengali",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
}

# Language-specific Wikipedia domains
WIKIPEDIA_DOMAINS = {
    "en": "en.wikipedia.org",
    "ta": "ta.wikipedia.org",
    "hi": "hi.wikipedia.org",
    "te": "te.wikipedia.org",
    "ml": "ml.wikipedia.org",
    "kn": "kn.wikipedia.org",
    "bn": "bn.wikipedia.org",
    "ar": "ar.wikipedia.org",
    "zh": "zh.wikipedia.org",
    "ja": "ja.wikipedia.org",
    "ko": "ko.wikipedia.org",
    "fr": "fr.wikipedia.org",
    "de": "de.wikipedia.org",
    "es": "es.wikipedia.org",
}


def detect_language(text: str) -> str:
    """Detect language from text (basic heuristic)."""
    # Check for non-ASCII characters
    if any(ord(c) > 127 for c in text):
        # Very basic detection - could be improved
        return "unknown"
    return "en"


def get_wikipedia_domain(lang: str) -> str:
    """Get Wikipedia domain for a language."""
    return WIKIPEDIA_DOMAINS.get(lang, "en.wikipedia.org")


# ===========================================================================
# Domain Capability Profiles
# ===========================================================================

DOMAIN_PROFILES = {
    "github.com": {
        "capabilities": ["search", "repository", "issues", "pull_requests", "raw_files", "api"],
        "best_source": "github",
        "api_endpoint": "https://api.github.com",
        "authentication": "optional",
    },
    "youtube.com": {
        "capabilities": ["search", "video", "metadata", "transcript"],
        "best_source": "youtube",
        "api_endpoint": None,
        "authentication": False,
    },
    "reddit.com": {
        "capabilities": ["search", "posts", "comments", "subreddits"],
        "best_source": "reddit",
        "api_endpoint": None,
        "authentication": False,
    },
    "stackoverflow.com": {
        "capabilities": ["search", "questions", "answers", "tags"],
        "best_source": "stackoverflow",
        "api_endpoint": "https://api.stackexchange.com",
        "authentication": False,
    },
    "bbc.com": {
        "capabilities": ["news", "rss", "search"],
        "best_source": "ddgs",
        "api_endpoint": None,
        "authentication": False,
    },
    "wikipedia.org": {
        "capabilities": ["search", "articles", "api", "structured_data"],
        "best_source": "wikipedia",
        "api_endpoint": "https://en.wikipedia.org/w/api.php",
        "authentication": False,
    },
}


def get_domain_profile(url: str) -> Dict[str, Any]:
    """Get capability profile for a domain."""
    domain = urlparse(url).netloc.replace("www.", "")
    
    for pattern, profile in DOMAIN_PROFILES.items():
        if domain.endswith(pattern):
            return {**profile, "domain": domain}
    
    return {
        "domain": domain,
        "capabilities": ["web"],
        "best_source": "ddgs",
        "api_endpoint": None,
        "authentication": False,
    }
