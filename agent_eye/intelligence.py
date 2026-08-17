# -*- coding: utf-8 -*-
"""AgentEye — Production Intelligence Layer.

URL canonicalization, source ranking, citation system, evidence engine.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


# ===========================================================================
# URL Canonicalization
# ===========================================================================

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "ref_src", "ref_url", "spm",
    "from", "share", "feature", "ab_test", "mc_cid", "mc_eid",
}


def canonicalize_url(url: str) -> str:
    """Canonicalize URL for deduplication.
    
    - Lowercases domain
    - Removes www prefix
    - Removes tracking parameters
    - Normalizes path (remove trailing slash except for root)
    - Sorts query parameters
    - Removes fragment
    """
    try:
        parsed = urlparse(url.strip())
        
        # Lowercase and remove www
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        # Normalize path
        path = parsed.path.rstrip("/") or "/"
        
        # Remove tracking params
        query = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in sorted(query.items()) if k.lower() not in TRACKING_PARAMS}
        new_query = urlencode(cleaned, doseq=True)
        
        # Rebuild without fragment
        return urlunparse((
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.params,
            new_query,
            "",  # Remove fragment
        ))
    except Exception:
        return url


def content_hash(text: str) -> str:
    """Create normalized content hash for deduplication."""
    # Normalize: lowercase, collapse whitespace, strip
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()


# ===========================================================================
# Source Ranking
# ===========================================================================

DOMAIN_AUTHORITY = {
    # Academic / Research
    "arxiv.org": 0.97, "pubmed.ncbi.nlm.nih.gov": 0.97, "nature.com": 0.95,
    "science.org": 0.95, "ieee.org": 0.92, "acm.org": 0.92, "springer.com": 0.90,
    
    # Code
    "github.com": 0.96, "gitlab.com": 0.88, "bitbucket.org": 0.82,
    "stackoverflow.com": 0.92, "docs.python.org": 0.90, "developer.mozilla.org": 0.90,
    
    # Government / Official
    ".gov": 0.95, ".edu": 0.90, ".ac.uk": 0.90,
    "data.gov": 0.92, "worldbank.org": 0.92, "un.org": 0.92,
    
    # News / Reference
    "bbc.com": 0.90, "reuters.com": 0.90, "nytimes.com": 0.88,
    "theguardian.com": 0.88, "wikipedia.org": 0.93,
    
    # Tech
    "news.ycombinator.com": 0.85, "techcrunch.com": 0.78,
    "theverge.com": 0.78, "arstechnica.com": 0.82,
    
    # Social
    "reddit.com": 0.75, "youtube.com": 0.80,
}


def get_domain_authority(domain_or_url: str) -> float:
    """Get authority score for a domain or URL."""
    # Handle both full URLs and bare domains
    if "://" in domain_or_url:
        domain = urlparse(domain_or_url).netloc.lower()
    else:
        domain = domain_or_url.lower()
    
    domain = domain.replace("www.", "")
    
    # Check exact match first
    if domain in DOMAIN_AUTHORITY:
        return DOMAIN_AUTHORITY[domain]
    
    # Check partial matches
    for pattern, score in DOMAIN_AUTHORITY.items():
        if pattern.startswith("."):
            if domain.endswith(pattern):
                return score
        elif domain.endswith("." + pattern) or domain == pattern:
            return score
    
    return 0.50  # Default for unknown domains


def calculate_freshness_score(result: Dict[str, Any]) -> float:
    """Calculate freshness score based on date metadata."""
    timestamp = result.get("date") or result.get("timestamp") or result.get("published_at") or result.get("created")
    
    if not timestamp:
        return 0.30  # Unknown date gets low freshness
    
    try:
        if isinstance(timestamp, (int, float)):
            if timestamp > 1e12:
                timestamp = timestamp / 1000
            age_hours = (time.time() - timestamp) / 3600
        elif isinstance(timestamp, str):
            # Try parsing ISO format
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            except Exception:
                age_hours = 24
        else:
            age_hours = 24
        
        # Score: 1.0 = now, 0.0 = very old
        if age_hours < 1:
            return 1.0
        elif age_hours < 24:
            return 0.95
        elif age_hours < 168:  # 1 week
            return 0.85
        elif age_hours < 720:  # 30 days
            return 0.70
        elif age_hours < 2160:  # 90 days
            return 0.50
        elif age_hours < 8760:  # 1 year
            return 0.35
        else:
            return 0.15
    except Exception:
        return 0.30


def rank_results(results: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
    """Rank results using relevance + freshness + authority."""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for result in results:
        # Relevance score (35%)
        relevance = 0.5
        title = result.get("title", "").lower()
        desc = result.get("description", "").lower()
        
        title_matches = sum(1 for w in query_words if w in title)
        desc_matches = sum(1 for w in query_words if w in desc)
        
        if query_words:
            relevance = (title_matches * 2 + desc_matches) / max(len(query_words) * 3, 1)
            relevance = min(relevance, 1.0)
        
        # Freshness score (25%)
        freshness = calculate_freshness_score(result)
        
        # Authority score (25%)
        authority = get_domain_authority(result.get("url", ""))
        
        # Content completeness (15%)
        completeness = 0.0
        if result.get("title") and len(result["title"]) > 10:
            completeness += 0.05
        if result.get("description") and len(result["description"]) > 50:
            completeness += 0.05
        if result.get("json_ld") or result.get("open_graph"):
            completeness += 0.05
        
        # Combined score
        result["relevance_score"] = round(relevance, 3)
        result["freshness_score"] = round(freshness, 3)
        result["authority_score"] = round(authority, 3)
        result["quality_score"] = round(
            (relevance * 0.35 + freshness * 0.25 + authority * 0.25 + completeness * 0.15),
            3
        )
    
    results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    return results


# ===========================================================================
# Citation System
# ===========================================================================

class Citation:
    """A single citation."""
    
    def __init__(self, claim_id: str, source_url: str, title: str = "", evidence: str = ""):
        self.claim_id = claim_id
        self.source_url = source_url
        self.title = title
        self.evidence = evidence
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "claim_id": self.claim_id,
            "source_url": self.source_url,
            "title": self.title,
            "evidence": self.evidence[:200],
        }


class CitationEngine:
    """Track and generate citations."""
    
    def __init__(self):
        self.citations: Dict[str, Citation] = {}
        self.claim_counter = 0
    
    def add_claim(self, claim_text: str, source_url: str, title: str = "", evidence: str = "") -> str:
        """Add a claim and return its citation ID."""
        self.claim_counter += 1
        claim_id = f"C{self.claim_counter}"
        
        self.citations[claim_id] = Citation(
            claim_id=claim_id,
            source_url=source_url,
            title=title,
            evidence=evidence,
        )
        
        return claim_id
    
    def get_citation(self, claim_id: str) -> Optional[Citation]:
        return self.citations.get(claim_id)
    
    def render_citation(self, claim_id: str) -> str:
        """Render citation as markdown link."""
        cite = self.citations.get(claim_id)
        if not cite:
            return f"[{claim_id}](#)"
        
        title = cite.title or cite.source_url
        return f"[{title}]({cite.source_url})"
    
    def render_all(self) -> List[Dict[str, Any]]:
        """Render all citations as list."""
        return [cite.to_dict() for cite in self.citations.values()]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_citations": len(self.citations),
            "citations": {k: v.to_dict() for k, v in self.citations.items()},
        }


# ===========================================================================
# Evidence Engine
# ===========================================================================

class Evidence:
    """A piece of evidence."""
    
    def __init__(self, text: str, source_url: str, confidence: float = 0.5):
        self.text = text
        self.source_url = source_url
        self.confidence = confidence
        self.sources: List[str] = []
    
    def add_source(self, source_url: str):
        if source_url not in self.sources:
            self.sources.append(source_url)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "source_count": len(self.sources),
        }


class EvidenceEngine:
    """Track and verify evidence."""
    
    def __init__(self):
        self.evidence_list: List[Evidence] = []
        self.claim_counter = 0
    
    def add_evidence(self, text: str, source_url: str, confidence: float = 0.5) -> Evidence:
        """Add evidence."""
        ev = Evidence(text, source_url, confidence)
        self.evidence_list.append(ev)
        return ev
    
    def verify_claims(self) -> List[Dict[str, Any]]:
        """Verify claims across sources."""
        verified = []
        
        for ev in self.evidence_list:
            result = {
                "claim": ev.text,
                "confidence": ev.confidence,
                "sources": ev.sources if ev.sources else [ev.source_url],
                "status": "single_source",
            }
            
            if len(ev.sources) > 1:
                result["status"] = "cross_verified"
                result["confidence"] = min(1.0, ev.confidence * 1.2)
            
            verified.append(result)
        
        return verified
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_evidence": len(self.evidence_list),
            "avg_confidence": sum(e.confidence for e in self.evidence_list) / max(len(self.evidence_list), 1),
        }


# ===========================================================================
# Freshness Interpretation
# ===========================================================================

FRESHNESS_MAP = {
    "today": (1, "day"),
    "now": (1, "day"),
    "currently": (1, "day"),
    "this week": (7, "day"),
    "this month": (30, "day"),
    "latest": (30, "day"),
    "recent": (30, "day"),
    "recently": (30, "day"),
    "new": (30, "day"),
    "2026": (365, "day"),
    "2025": (365 * 2, "day"),
    "last week": (14, "day"),
    "last month": (60, "day"),
    "yesterday": (2, "day"),
}


def interpret_freshness(query: str) -> Optional[Tuple[int, str]]:
    """Extract freshness requirement from query.
    
    Returns (duration, unit) or None.
    """
    query_lower = query.lower()
    
    for phrase, (duration, unit) in FRESHNESS_MAP.items():
        if phrase in query_lower:
            return (duration, unit)
    
    return None


# ===========================================================================
# Failure Handling
# ===========================================================================

class FailureHandler:
    """Handle failures gracefully."""
    
    def __init__(self):
        self.domains_blocked: set = set()
        self.domains_slow: set = set()
        self.failure_count: Dict[str, int] = {}
    
    def record_failure(self, domain: str, error: str):
        """Record a failure for a domain."""
        self.failure_count[domain] = self.failure_count.get(domain, 0) + 1
        
        if "403" in error or "blocked" in error.lower():
            self.domains_blocked.add(domain)
        if "timeout" in error.lower():
            self.domains_slow.add(domain)
    
    def is_blocked(self, domain: str) -> bool:
        """Check if domain is blocked."""
        return domain in self.domains_blocked or self.failure_count.get(domain, 0) > 3
    
    def should_skip(self, url: str) -> bool:
        """Check if URL should be skipped."""
        domain = urlparse(url).netloc.replace("www.", "")
        return self.is_blocked(domain)


# ===========================================================================
# Domain Intelligence
# ===========================================================================

class DomainProfile:
    """Domain intelligence profile."""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.capabilities: Dict[str, bool] = {}
        self.authority: float = 0.5
        self.last_checked: float = 0
    
    def set_capability(self, name: str, value: bool):
        self.capabilities[name] = value
        self.last_checked = time.time()
    
    def get_capability(self, name: str) -> bool:
        return self.capabilities.get(name, False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "capabilities": self.capabilities,
            "authority": self.authority,
            "last_checked": self.last_checked,
        }


class DomainIntelligence:
    """Manage domain intelligence."""
    
    def __init__(self):
        self.profiles: Dict[str, DomainProfile] = {}
    
    def get_profile(self, domain: str) -> DomainProfile:
        if domain not in self.profiles:
            self.profiles[domain] = DomainProfile(domain)
        return self.profiles[domain]
    
    def update_profile(self, domain: str, capabilities: Dict[str, bool]):
        profile = self.get_profile(domain)
        for k, v in capabilities.items():
            profile.set_capability(k, v)
    
    def get_authority(self, domain: str) -> float:
        profile = self.get_profile(domain)
        return profile.authority
    
    def set_authority(self, domain: str, authority: float):
        profile = self.get_profile(domain)
        profile.authority = authority


# ===========================================================================
# Database Schema for Production
# ===========================================================================

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    author TEXT,
    published_at TEXT,
    modified_at TEXT,
    fetched_at TEXT NOT NULL,
    authority_score REAL DEFAULT 0.5,
    content_hash TEXT,
    UNIQUE(canonical_url)
);

CREATE TABLE IF NOT EXISTS search_sessions (
    session_id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    intent TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_queries INTEGER DEFAULT 0,
    total_pages_fetched INTEGER DEFAULT 0,
    final_confidence REAL
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    source_id TEXT NOT NULL,
    evidence TEXT,
    confidence REAL NOT NULL,
    status TEXT DEFAULT 'unverified',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS citations (
    citation_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    display_order INTEGER
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    source_url TEXT NOT NULL,
    confidence REAL NOT NULL,
    verified INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_events (
    event_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT,
    detected_at TEXT NOT NULL,
    consumed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS monitoring_jobs (
    monitor_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    check_interval_seconds INTEGER DEFAULT 3600,
    method TEXT DEFAULT 'etag',
    last_checked_at TEXT,
    last_hash TEXT,
    active INTEGER DEFAULT 1
);

CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
    claim, content='evidence', content_rowid='rowid'
);
"""


def init_database(db_path: str):
    """Initialize database with schema."""
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA)
    conn.commit()
    conn.close()
