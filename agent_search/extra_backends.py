# -*- coding: utf-8 -*-
"""Agent Search Lite — Additional search backends and utilities.

MDN Web Docs, Dev.to, search suggestions, clustering, multi-language.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_MDN_API = "https://developer.mozilla.org/api/v1"
_DEVTO_API = "https://dev.to/api"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/3.1; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# MDN Web Docs Backend
# ---------------------------------------------------------------------------

def mdn_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search MDN Web Docs for web documentation.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_MDN_API}/search",
            params={
                "q": query,
                "locale": "en-US",
                "limit": limit,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        documents = data.get("documents", [])
        if not documents:
            return None
        
        results = []
        for i, doc in enumerate(documents[:limit]):
            results.append({
                "title": doc.get("title", ""),
                "url": f"https://developer.mozilla.org{doc.get('mdn_url', '')}",
                "description": doc.get("summary", ""),
                "source": "mdn",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("MDN search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Dev.to Backend
# ---------------------------------------------------------------------------

def devto_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Dev.to for developer articles.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_DEVTO_API}/articles",
            params={
                "per_page": limit,
                "page": 1,
                "search": query,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data:
            return None
        
        results = []
        for i, article in enumerate(data[:limit]):
            results.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "description": article.get("description", "")[:300],
                "author": article.get("user", {}).get("name", ""),
                "tags": ", ".join(article.get("tag_list", [])),
                "source": "devto",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Dev.to search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Search Suggestions
# ---------------------------------------------------------------------------

def get_suggestions(query: str, limit: int = 5) -> List[str]:
    """Get search suggestions from DuckDuckGo.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            "https://duckduckgo.com/ac/",
            params={"q": query, "type": "list"},
            headers={"User-Agent": _UA},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        
        suggestions = []
        if isinstance(data, list) and len(data) > 1:
            for item in data[1][:limit]:
                if isinstance(item, str):
                    suggestions.append(item)
        
        return suggestions
        
    except Exception as exc:
        logger.debug("Suggestions failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Multi-language Wikipedia
# ---------------------------------------------------------------------------

WIKI_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "hi": "हिन्दी",
    "ar": "العربية",
    "pt": "Português",
    "ru": "Русский",
    "it": "Italiano",
}

def wikipedia_search_multi(query: str, limit: int = 5, lang: str = "en") -> Optional[Dict[str, Any]]:
    """Search Wikipedia in multiple languages."""
    try:
        base_url = f"https://{lang}.wikipedia.org/w/api.php"
        
        resp = httpx.get(
            base_url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        search_results = data.get("query", {}).get("search", [])
        
        if not search_results:
            return None
        
        results = []
        for r in search_results:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            snippet = re.sub(r'<[^>]+>', '', snippet)
            
            import urllib.parse
            results.append({
                "title": title,
                "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                "description": snippet,
                "language": lang,
                "source": "wikipedia",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Wikipedia multi search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Result Clustering
# ---------------------------------------------------------------------------

def cluster_results(results: list) -> Dict[str, list]:
    """Cluster results by similarity.
    
    Uses simple title similarity (Jaccard index).
    Returns clusters with their member results.
    """
    if not results:
        return {}
    
    clusters = {}
    visited = set()
    
    for i, result in enumerate(results):
        if i in visited:
            continue
        
        title = result.get("title", "")
        cluster_key = _generate_cluster_key(title)
        
        if cluster_key not in clusters:
            clusters[cluster_key] = []
        
        clusters[cluster_key].append(result)
        visited.add(i)
        
        # Find similar results
        for j, other in enumerate(results):
            if j in visited:
                continue
            
            other_title = other.get("title", "")
            similarity = _calculate_similarity(title, other_title)
            
            if similarity > 0.3:
                clusters[cluster_key].append(other)
                visited.add(j)
    
    return clusters


def _generate_cluster_key(title: str) -> str:
    """Generate a cluster key from title."""
    # Extract key terms (skip common words)
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall", "can", "need", "dare", "ought", "used", "how", "what", "why", "when", "where", "which", "who", "whom", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}
    
    words = title.lower().split()
    key_terms = [w for w in words if w not in stop_words and len(w) > 2]
    
    return " ".join(key_terms[:3])


def _calculate_similarity(title1: str, title2: str) -> float:
    """Calculate Jaccard similarity between two titles."""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Result Freshness
# ---------------------------------------------------------------------------

def filter_by_freshness(results: list, max_age_days: int = 365) -> list:
    """Filter results by freshness (if date information available)."""
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    filtered = []
    
    for r in results:
        # Check various date fields
        date_str = r.get("published") or r.get("timestamp") or r.get("date")
        
        if date_str:
            try:
                # Try various date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
                    try:
                        pub_date = datetime.strptime(date_str[:10], fmt)
                        if pub_date >= cutoff:
                            filtered.append(r)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format matched, include result
                    filtered.append(r)
            except Exception:
                filtered.append(r)
        else:
            # No date info, include result
            filtered.append(r)
    
    return filtered


def sort_by_freshness(results: list) -> list:
    """Sort results by publication date (newest first)."""
    from datetime import datetime
    
    def get_date(result):
        date_str = result.get("published") or result.get("timestamp") or result.get("date")
        if date_str:
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
            except ValueError:
                pass
        return datetime.min
    
    results.sort(key=get_date, reverse=True)
    return results
