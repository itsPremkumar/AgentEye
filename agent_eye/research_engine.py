# -*- coding: utf-8 -*-
"""Agent Search Lite — Research Engine.

Multi-step research with citations, source verification, and query expansion.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Research Mode
# ---------------------------------------------------------------------------

def research(
    question: str,
    sources: int = 10,
    depth: int = 2,
    mode: str = "general",
) -> Dict[str, Any]:
    """Conduct multi-step research on a question."""
    # Local import to avoid circular import
    from agent_eye.core import AgentSearchLite
    search = AgentSearchLite()
    
    result = {
        "question": question,
        "sources_consulted": 0,
        "findings": [],
        "citations": [],
        "summary": "",
        "confidence": 0.0,
    }
    
    # Step 1: Query expansion
    queries = _expand_query(question, depth)
    
    # Step 2: Search with expanded queries
    all_results = []
    for query in queries[:depth * 3]:
        search_result = search.search(query, limit=sources // len(queries) + 1, mode=mode, use_cache=True)
        if search_result["success"]:
            all_results.extend(search_result["data"]["web"])
    
    # Step 3: Deduplicate and rank
    unique_results = _deduplicate_results(all_results)
    ranked_results = _rank_by_relevance(unique_results, question)
    
    # Step 4: Extract key findings
    findings = _extract_findings(ranked_results[:sources], question)
    result["findings"] = findings
    
    # Step 5: Generate citations
    result["citations"] = _generate_citations(ranked_results[:sources])
    
    # Step 6: Calculate confidence
    result["confidence"] = _calculate_confidence(findings, sources)
    
    # Step 7: Generate summary
    result["summary"] = _generate_summary(findings, question)
    
    result["sources_consulted"] = len(ranked_results[:sources])
    
    return result


def _expand_query(question: str, depth: int) -> List[str]:
    """Expand a research question into multiple search queries."""
    queries = [question]
    
    # Add variations
    if "compare" in question.lower():
        queries.append(question.replace("compare", "vs"))
        queries.append(question.replace("compare", "difference between"))
    
    if "best" in question.lower():
        queries.append(question.replace("best", "top"))
        queries.append(question.replace("best", "recommended"))
    
    if "how" in question.lower():
        queries.append(question.replace("how", "guide to"))
        queries.append(question.replace("how", "tutorial"))
    
    # Add depth-based variations
    if depth >= 2:
        queries.append(f"{question} 2024 2025")
        queries.append(f"{question} latest")
    
    if depth >= 3:
        queries.append(f"{question} research paper")
        queries.append(f"{question} analysis")
    
    return list(set(queries))


def _deduplicate_results(results: List[Dict]) -> List[Dict]:
    """Deduplicate results by URL."""
    seen = set()
    unique = []
    
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    
    return unique


def _rank_by_relevance(results: List[Dict], question: str) -> List[Dict]:
    """Rank results by relevance to the question."""
    question_words = set(question.lower().split())
    
    for r in results:
        title = r.get("title", "").lower()
        desc = r.get("description", "").lower()
        
        # Calculate relevance score
        title_matches = sum(1 for w in question_words if w in title)
        desc_matches = sum(1 for w in question_words if w in desc)
        
        r["relevance_score"] = (title_matches * 2 + desc_matches) / max(len(question_words), 1)
    
    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return results


def _extract_findings(results: List[Dict], question: str) -> List[Dict]:
    """Extract key findings from search results."""
    findings = []
    
    for r in results:
        finding = {
            "source": r.get("source", ""),
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "snippet": r.get("description", "")[:200],
            "relevance": r.get("relevance_score", 0),
        }
        findings.append(finding)
    
    return findings


def _generate_citations(results: List[Dict]) -> List[Dict]:
    """Generate citations for sources."""
    citations = []
    
    for i, r in enumerate(results):
        citation = {
            "id": i + 1,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": r.get("source", ""),
            "accessed": time.strftime("%Y-%m-%d"),
        }
        citations.append(citation)
    
    return citations


def _calculate_confidence(findings: List[Dict], target_sources: int) -> float:
    """Calculate confidence score based on findings."""
    if not findings:
        return 0.0
    
    # Based on number of sources and average relevance
    source_ratio = min(len(findings) / target_sources, 1.0)
    avg_relevance = sum(f.get("relevance", 0) for f in findings) / len(findings)
    
    return round((source_ratio * 0.5 + avg_relevance * 0.5), 2)


def _generate_summary(findings: List[Dict], question: str) -> str:
    """Generate a summary of findings."""
    if not findings:
        return "No findings available."
    
    # Simple summary generation
    summary_parts = [f"Research on: {question}\n"]
    summary_parts.append(f"Based on {len(findings)} sources:\n")
    
    for i, finding in enumerate(findings[:5]):
        summary_parts.append(f"{i+1}. {finding['title']}")
        if finding.get("snippet"):
            summary_parts.append(f"   {finding['snippet'][:100]}...")
        summary_parts.append("")
    
    return "\n".join(summary_parts)


# ---------------------------------------------------------------------------
# Source Verification
# ---------------------------------------------------------------------------

def verify_source(url: str) -> Dict[str, Any]:
    """Verify a source's reliability and authority."""
    result = {
        "url": url,
        "domain": "",
        "reliable": False,
        "category": "",
        "notes": [],
    }
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        result["domain"] = domain
        
        # Check against known reliable sources
        reliable_domains = {
            "github.com": ("code", True),
            "stackoverflow.com": ("code", True),
            "arxiv.org": ("academic", True),
            "pubmed.ncbi.nlm.nih.gov": ("academic", True),
            "wikipedia.org": ("encyclopedia", True),
            "news.ycombinator.com": ("tech_news", True),
            "bbc.com": ("news", True),
            "reuters.com": ("news", True),
            "nature.com": ("academic", True),
            "science.org": ("academic", True),
        }
        
        for reliable_domain, (category, reliable) in reliable_domains.items():
            if domain.endswith(reliable_domain):
                result["category"] = category
                result["reliable"] = reliable
                break
        
        if not result["category"]:
            result["category"] = "unknown"
            result["notes"].append("Unknown domain - verify manually")
        
    except Exception as exc:
        result["notes"].append(f"Verification failed: {exc}")
    
    return result


# ---------------------------------------------------------------------------
# Query Expansion
# ---------------------------------------------------------------------------

def expand_query(query: str, max_expansions: int = 5) -> List[str]:
    """Expand a query with synonyms and variations."""
    expansions = [query]
    
    # Common expansions
    expansions.append(f"{query} 2024 2025")
    expansions.append(f"{query} latest")
    expansions.append(f"{query} guide")
    expansions.append(f"{query} tutorial")
    
    return expansions[:max_expansions]
