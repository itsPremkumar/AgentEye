# -*- coding: utf-8 -*-
"""AgentLens — Website Capability Detector.

Detects what a website supports: RSS, sitemap, API, JSON-LD, etc.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Capability Detection
# ---------------------------------------------------------------------------

def detect_capabilities(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Detect what a website supports.
    
    Returns:
        {
            "url": "https://example.com",
            "static_html": true,
            "dynamic_js": false,
            "rss": ["https://example.com/feed"],
            "sitemap": ["https://example.com/sitemap.xml"],
            "json_ld": true,
            "open_graph": true,
            "microdata": false,
            "api": false,
            "graphql": false,
            "websocket": false,
            "sse": false,
            "authentication_required": false,
            "robots_txt": true,
            "well_known": [],
            "recommended_strategy": "rss"
        }
    """
    result = {
        "url": url,
        "static_html": False,
        "dynamic_js": False,
        "rss": [],
        "sitemap": [],
        "json_ld": False,
        "open_graph": False,
        "microdata": False,
        "api": False,
        "graphql": False,
        "websocket": False,
        "sse": False,
        "authentication_required": False,
        "robots_txt": False,
        "well_known": [],
        "recommended_strategy": "http",
    }
    
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check robots.txt
        result["robots_txt"] = _check_robots(base_url, timeout)
        
        # Check well-known endpoints
        result["well_known"] = _check_well_known(base_url, timeout)
        
        # Check common feed locations
        result["rss"] = _check_feeds(base_url, timeout)
        
        # Check sitemaps
        result["sitemap"] = _check_sitemaps(base_url, timeout)
        
        # Fetch page and analyze
        page_data = _fetch_and_analyze(url, timeout)
        result.update(page_data)
        
        # Determine recommended strategy
        result["recommended_strategy"] = _determine_strategy(result)
        
    except Exception as exc:
        logger.debug(f"Capability detection failed for {url}: {exc}")
    
    return result


def _check_robots(base_url: str, timeout: int) -> bool:
    """Check if robots.txt exists."""
    try:
        resp = httpx.get(
            f"{base_url}/robots.txt",
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _check_well_known(base_url: str, timeout: int) -> List[str]:
    """Check .well-known/ endpoints."""
    found = []
    
    endpoints = [
        "/.well-known/",
        "/.well-known/host-meta",
        "/.well-known/nodeinfo",
        "/.well-known/webfinger",
    ]
    
    for endpoint in endpoints:
        try:
            resp = httpx.get(
                f"{base_url}{endpoint}",
                headers={"User-Agent": ua_rotator.get()},
                timeout=5,
            )
            if resp.status_code == 200:
                found.append(endpoint)
        except Exception:
            continue
    
    return found


def _check_feeds(base_url: str, timeout: int) -> List[str]:
    """Check common RSS/Atom feed locations."""
    found = []
    
    feed_paths = [
        "/feed",
        "/feed.xml",
        "/rss",
        "/rss.xml",
        "/atom.xml",
        "/feeds/posts/default",
        "/index.xml",
        "/blog/feed",
        "/blog/feed.xml",
        "/feed/rss",
        "/feed/atom",
        "/rss feed",
    ]
    
    for path in feed_paths:
        try:
            resp = httpx.head(
                f"{base_url}{path}",
                headers={"User-Agent": ua_rotator.get()},
                timeout=5,
            )
            if resp.status_code == 200:
                found.append(f"{base_url}{path}")
        except Exception:
            continue
    
    return found


def _check_sitemaps(base_url: str, timeout: int) -> List[str]:
    """Check common sitemap locations."""
    found = []
    
    sitemap_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps.xml",
        "/sitemap/sitemap.xml",
        "/wp-sitemap.xml",
    ]
    
    for path in sitemap_paths:
        try:
            resp = httpx.head(
                f"{base_url}{path}",
                headers={"User-Agent": ua_rotator.get()},
                timeout=5,
            )
            if resp.status_code == 200:
                found.append(f"{base_url}{path}")
        except Exception:
            continue
    
    return found


def _fetch_and_analyze(url: str, timeout: int) -> Dict[str, Any]:
    """Fetch page and analyze its content."""
    result = {
        "static_html": False,
        "dynamic_js": False,
        "json_ld": False,
        "open_graph": False,
        "microdata": False,
        "api": False,
        "graphql": False,
        "websocket": False,
        "sse": False,
        "authentication_required": False,
    }
    
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        
        html = resp.text
        content_type = resp.headers.get("content-type", "")
        
        # Check if it's HTML
        if "text/html" in content_type:
            result["static_html"] = True
            
            # Check for JSON-LD
            if '"@type"' in html or '"@context"' in html:
                result["json_ld"] = True
            
            # Check for Open Graph
            if 'property="og:' in html or 'name="og:' in html:
                result["open_graph"] = True
            
            # Check for microdata
            if 'itemscope' in html or 'itemtype' in html:
                result["microdata"] = True
            
            # Check for GraphQL
            if '/graphql' in html or 'graphql' in html.lower():
                result["graphql"] = True
            
            # Check for WebSocket
            if 'websocket' in html.lower() or 'new WebSocket' in html:
                result["websocket"] = True
            
            # Check for SSE
            if 'EventSource' in html or 'text/event-stream' in html:
                result["sse"] = True
            
            # Check for API endpoints
            if '/api/' in html or '/api/v' in html:
                result["api"] = True
            
            # Check for dynamic JS frameworks
            js_frameworks = ['react', 'vue', 'angular', 'next', 'nuxt', 'gatsby']
            for framework in js_frameworks:
                if framework in html.lower():
                    result["dynamic_js"] = True
                    break
            
            # Check for authentication walls
            auth_indicators = ['login', 'sign in', 'authenticate', 'signin']
            for indicator in auth_indicators:
                if indicator in html.lower()[:5000]:
                    result["authentication_required"] = True
                    break
        
    except Exception as exc:
        logger.debug(f"Page analysis failed: {exc}")
    
    return result


def _determine_strategy(capabilities: Dict[str, Any]) -> str:
    """Determine the best strategy to fetch data from this website."""
    # Priority order
    if capabilities.get("rss"):
        return "rss"
    
    if capabilities.get("sitemap"):
        return "sitemap"
    
    if capabilities.get("json_ld"):
        return "json_ld"
    
    if capabilities.get("api"):
        return "api"
    
    if capabilities.get("open_graph"):
        return "open_graph"
    
    if capabilities.get("dynamic_js"):
        return "browser"
    
    if capabilities.get("static_html"):
        return "http"
    
    return "unknown"


# ---------------------------------------------------------------------------
# Hidden API Discovery
# ---------------------------------------------------------------------------

def discover_api_endpoints(url: str, timeout: int = 15) -> List[str]:
    """Discover potential API endpoints in page HTML."""
    found = []
    
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
        
        # Pattern matching for common API endpoints
        patterns = [
            r'["\']([^"\']*\/api\/[^"\']+)["\']',
            r'["\']([^"\']*\/v[0-9]+\/[^"\']+)["\']',
            r'["\']([^"\']*\/graphql[^"\']*)["\']',
            r'["\']([^"\']*\/data\.json)["\']',
            r'["\']([^"\']*\/json[^"\']*)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.get\(["\']([^"\']+)["\']',
            r'\.ajax\(\{[^}]*url:\s*["\']([^"\']+)["\']',
        ]
        
        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match not in seen and not match.startswith('http'):
                    # Convert relative to absolute
                    from urllib.parse import urljoin
                    absolute = urljoin(url, match)
                    seen.add(match)
                    found.append(absolute)
        
    except Exception as exc:
        logger.debug(f"API discovery failed: {exc}")
    
    return found[:20]  # Limit results


# ---------------------------------------------------------------------------
# Content Classification
# ---------------------------------------------------------------------------

def classify_website(url: str, timeout: int = 15) -> str:
    """Classify website type based on content."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text.lower()
        
        # Classification rules
        indicators = {
            "blog": ["blog", "post", "article", "feed"],
            "news": ["news", "breaking", "headline", "latest"],
            "ecommerce": ["product", "price", "cart", "buy", "shop"],
            "documentation": ["docs", "documentation", "api reference", "guide"],
            "forum": ["forum", "thread", "topic", "reply", "post"],
            "social": ["profile", "follower", "following", "like", "share"],
            "video": ["video", "watch", "stream", "channel"],
            "portfolio": ["portfolio", "project", "work", "gallery"],
            "government": ["gov", "official", "agency", "department"],
            "academic": ["research", "paper", "journal", "study", "university"],
        }
        
        scores = {}
        for category, keywords in indicators.items():
            score = sum(1 for kw in keywords if kw in html[:10000])
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "unknown"
        
    except Exception:
        return "unknown"
