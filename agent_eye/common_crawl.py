# -*- coding: utf-8 -*-
"""AgentLens — Common Crawl Integration.

Search and fetch historical web data from Common Crawl's free archive.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)

COMMON_CRAWL_API = "https://index.commoncrawl.org"
COMMON_CRAWL_DATA = "https://data.commoncrawl.org"


# ---------------------------------------------------------------------------
# Common Crawl Index Search
# ---------------------------------------------------------------------------

def search_common_crawl(
    query: str,
    limit: int = 10,
    crawl: str = "CC-MAIN-2025-13",
) -> Optional[Dict[str, Any]]:
    """Search Common Crawl index for historical web pages.
    
    Args:
        query: Search query (domain or URL pattern)
        limit: Maximum results
        crawl: Crawl ID (default: latest 2025 crawl)
    
    Returns:
        Search results with URLs and metadata
    """
    try:
        # Use the Common Crawl index API
        url = f"{COMMON_CRAWL_API}/{crawl}-index"
        
        resp = httpx.get(
            url,
            params={
                "url": query,
                "output": "json",
                "limit": limit,
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=30,
        )
        resp.raise_for_status()
        
        results = []
        for line in resp.text.strip().split("\n"):
            if line:
                try:
                    data = json.loads(line)
                    results.append({
                        "url": data.get("url", ""),
                        "timestamp": data.get("timestamp", ""),
                        "status": data.get("status", ""),
                        "length": data.get("length", 0),
                        "mime": data.get("mime", ""),
                        "offset": data.get("offset", 0),
                        "filename": data.get("filename", ""),
                        "source": "common_crawl",
                        "position": len(results) + 1,
                    })
                except json.JSONDecodeError:
                    continue
        
        if results:
            return {"success": True, "data": {"web": results}}
        
        return None
    
    except Exception as exc:
        logger.debug(f"Common Crawl search failed: {exc}")
        return None


def search_domain(domain: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search for all pages from a domain in Common Crawl."""
    return search_common_crawl(f"{domain}/*", limit)


def search_url_pattern(pattern: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search for URLs matching a pattern in Common Crawl."""
    return search_common_crawl(pattern, limit)


# ---------------------------------------------------------------------------
# Common Crawl Page Fetch
# ---------------------------------------------------------------------------

def fetch_from_common_crawl(
    url: str,
    crawl: str = "CC-MAIN-2025-13",
) -> Optional[Dict[str, Any]]:
    """Fetch a specific page from Common Crawl archive.
    
    Args:
        url: The URL to fetch
        crawl: Crawl ID
    
    Returns:
        Page content and metadata
    """
    try:
        # First, find the page in the index
        index_url = f"{COMMON_CRAWL_API}/{crawl}-index"
        
        resp = httpx.get(
            index_url,
            params={
                "url": url,
                "output": "json",
                "limit": 1,
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=30,
        )
        resp.raise_for_status()
        
        # Parse the index response
        lines = resp.text.strip().split("\n")
        if not lines or not lines[0]:
            return None
        
        index_data = json.loads(lines[0])
        
        # Now fetch the actual page content
        offset = index_data.get("offset", 0)
        length = index_data.get("length", 0)
        filename = index_data.get("filename", "")
        
        if not filename:
            return None
        
        # Fetch from S3
        data_url = f"{COMMON_CRAWL_DATA}/{filename}"
        
        data_resp = httpx.get(
            data_url,
            headers={
                "User-Agent": ua_rotator.get(),
                "Range": f"bytes={offset}-{offset + length - 1}",
            },
            timeout=30,
        )
        data_resp.raise_for_status()
        
        # Parse WARC response
        content = data_resp.text
        
        # Extract HTTP response and body
        parts = content.split("\r\n\r\n", 2)
        if len(parts) >= 3:
            http_headers = parts[1]
            body = parts[2] if len(parts) > 2 else ""
        else:
            http_headers = ""
            body = content
        
        return {
            "url": url,
            "status": index_data.get("status", ""),
            "mime": index_data.get("mime", ""),
            "length": length,
            "timestamp": index_data.get("timestamp", ""),
            "http_headers": http_headers[:500],
            "body": body[:10000],
            "source": "common_crawl",
        }
    
    except Exception as exc:
        logger.debug(f"Common Crawl fetch failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Common Crawl Utilities
# ---------------------------------------------------------------------------

def list_crawls() -> List[Dict[str, str]]:
    """List available Common Crawl crawls."""
    try:
        resp = httpx.get(
            f"{COMMON_CRAWL_API}/crawl-index",
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        crawls = []
        for line in resp.text.strip().split("\n"):
            if line:
                try:
                    data = json.loads(line)
                    crawls.append({
                        "id": data.get("id", ""),
                        "name": data.get("name", ""),
                        "url": data.get("url", ""),
                    })
                except json.JSONDecodeError:
                    continue
        
        return crawls
    
    except Exception as exc:
        logger.debug(f"Failed to list crawls: {exc}")
        return []


def get_latest_crawl() -> str:
    """Get the latest crawl ID."""
    try:
        resp = httpx.get(
            f"{COMMON_CRAWL_API}/crawl-index",
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        lines = resp.text.strip().split("\n")
        if lines:
            data = json.loads(lines[-1])
            return data.get("id", "CC-MAIN-2025-13")
        
        return "CC-MAIN-2025-13"
    
    except Exception:
        return "CC-MAIN-2025-13"


# ---------------------------------------------------------------------------
# Domain Analysis
# ---------------------------------------------------------------------------

def analyze_domain(domain: str, limit: int = 100) -> Dict[str, Any]:
    """Analyze a domain's presence in Common Crawl."""
    results = search_domain(domain, limit)
    
    if not results or not results.get("success"):
        return {
            "domain": domain,
            "total_pages": 0,
            "status": "not_found",
        }
    
    pages = results["data"]["web"]
    
    # Analyze
    mime_types = {}
    status_codes = {}
    timestamps = []
    
    for page in pages:
        mime = page.get("mime", "unknown")
        status = page.get("status", "unknown")
        timestamp = page.get("timestamp", "")
        
        mime_types[mime] = mime_types.get(mime, 0) + 1
        status_codes[status] = status_codes.get(status, 0) + 1
        
        if timestamp:
            timestamps.append(timestamp)
    
    return {
        "domain": domain,
        "total_pages": len(pages),
        "mime_types": mime_types,
        "status_codes": status_codes,
        "earliest_page": min(timestamps) if timestamps else None,
        "latest_page": max(timestamps) if timestamps else None,
        "sample_urls": [p["url"] for p in pages[:5]],
    }
