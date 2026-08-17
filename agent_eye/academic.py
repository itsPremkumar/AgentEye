# -*- coding: utf-8 -*-
"""Agent Search Lite — Academic and factual search backends.

arXiv API for academic papers, Wikipedia API for factual/encyclopedic search.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_ARXIV_API = "http://export.arxiv.org/api/query"
_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_WIKIPEDIA_REST = "https://en.wikipedia.org/api/rest_v1"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/3.0; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# arXiv Backend
# ---------------------------------------------------------------------------

def arxiv_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search arXiv for academic papers.
    
    Uses the arXiv API (free, no key required).
    Returns papers with titles, abstracts, authors, and PDF links.
    """
    try:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        
        resp = httpx.get(
            _ARXIV_API,
            params=params,
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        results = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            
            # Get PDF link
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break
            
            # Get authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text)
            
            # Get categories
            categories = []
            for cat in entry.findall("atom:category", ns):
                categories.append(cat.get("term", ""))
            
            if title is not None:
                results.append({
                    "title": title.text.strip().replace("\n", " "),
                    "url": pdf_url or entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else "",
                    "description": summary.text.strip().replace("\n", " ")[:500] if summary is not None else "",
                    "authors": ", ".join(authors[:3]),
                    "categories": ", ".join(categories[:3]),
                    "published": published.text[:10] if published is not None else "",
                    "source": "arxiv",
                    "position": len(results) + 1,
                })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except ET.ParseError as exc:
        logger.debug("arXiv XML parse error: %s", exc)
    except httpx.HTTPStatusError as exc:
        logger.debug("arXiv HTTP error: %s", exc)
    except Exception as exc:
        logger.debug("arXiv search failed: %s", exc)
    
    return None


def arxiv_get_paper(arxiv_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific arXiv paper by ID."""
    try:
        params = {
            "id_list": arxiv_id,
            "max_results": 1,
        }
        
        resp = httpx.get(
            _ARXIV_API,
            params=params,
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None
        
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)
        
        return {
            "title": title.text.strip() if title is not None else "",
            "abstract": summary.text.strip() if summary is not None else "",
            "url": entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else "",
        }
        
    except Exception as exc:
        logger.debug("arXiv get paper failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Wikipedia Backend
# ---------------------------------------------------------------------------

def wikipedia_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Wikipedia for factual/encyclopedic content.
    
    Uses the Wikipedia API (free, no key required).
    Returns article titles, snippets, and URLs.
    """
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        
        resp = httpx.get(
            _WIKIPEDIA_API,
            params=params,
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
            # Clean HTML from snippet
            snippet = re.sub(r'<[^>]+>', '', snippet)
            
            results.append({
                "title": title,
                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                "description": snippet,
                "wordcount": r.get("wordcount", 0),
                "source": "wikipedia",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except httpx.HTTPStatusError as exc:
        logger.debug("Wikipedia HTTP error: %s", exc)
    except Exception as exc:
        logger.debug("Wikipedia search failed: %s", exc)
    
    return None


def wikipedia_get_summary(title: str) -> Optional[Dict[str, Any]]:
    """Get a Wikipedia article summary.
    
    Uses the REST API for clean, structured summaries.
    """
    try:
        resp = httpx.get(
            f"{_WIKIPEDIA_REST}/page/summary/{urllib.parse.quote(title)}",
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "extract": data.get("extract", ""),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "thumbnail": data.get("thumbnail", {}).get("source", ""),
        }
        
    except httpx.HTTPStatusError as exc:
        logger.debug("Wikipedia summary HTTP error: %s", exc)
    except Exception as exc:
        logger.debug("Wikipedia summary failed: %s", exc)
        return None


def wikipedia_get_full_article(title: str) -> Optional[str]:
    """Get full Wikipedia article content as plain text."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "exsectionformat": "plain",
            "format": "json",
        }
        
        resp = httpx.get(
            _WIKIPEDIA_API,
            params=params,
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            return page.get("extract", "")
        
    except Exception as exc:
        logger.debug("Wikipedia full article failed: %s", exc)
        return None
