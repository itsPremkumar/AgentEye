# -*- coding: utf-8 -*-
"""AgentLens — Social Media & Best-Effort Connectors.

Three-tier architecture:
- Tier A: Official public APIs (no auth required)
- Tier B: Best-effort public scraping (may break, rate-limited)
- Tier C: Optional user connectors (official APIs with keys)

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)

# Tier A endpoints (genuinely free, no auth)
BLUESKY_PUBLIC_API = "https://public.api.bsky.app/xrpc"
MASTODON_PUBLIC_API = "https://mastodon.social/api/v1"

# Tier B endpoints (best-effort, may break)
LINKEDIN_PUBLIC = "https://www.linkedin.com"
INSTAGRAM_PUBLIC = "https://www.instagram.com"
TIKTOK_PUBLIC = "https://www.tiktok.com"


# ===========================================================================
# TIER A — Official Public APIs (No Auth)
# ===========================================================================

def bluesky_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search Bluesky posts via public API (no auth required).
    
    Bluesky's public AppView endpoint allows unauthenticated access
    to public posts and profiles.
    """
    try:
        resp = httpx.get(
            f"{BLUESKY_PUBLIC_API}/app.bsky.feed.searchPosts",
            params={"q": query, "limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        posts = data.get("posts", [])
        if not posts:
            return None
        
        results = []
        for i, post in enumerate(posts[:limit]):
            author = post.get("author", {})
            record = post.get("record", {})
            
            results.append({
                "title": f"Post by {author.get('displayName', author.get('handle', ''))}",
                "url": f"https://bsky.app/profile/{author.get('handle', '')}/post/{post.get('uri', '').split('/')[-1]}",
                "description": record.get("text", "")[:300],
                "author": author.get("handle", ""),
                "created_at": record.get("createdAt", ""),
                "source": "bluesky",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Bluesky search failed: {exc}")
    return None


def bluesky_profile(handle: str) -> Optional[Dict[str, Any]]:
    """Get public Bluesky profile (no auth required)."""
    try:
        resp = httpx.get(
            f"{BLUESKY_PUBLIC_API}/app.bsky.actor.getProfile",
            params={"actor": handle},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "handle": data.get("handle", ""),
            "display_name": data.get("displayName", ""),
            "description": data.get("description", ""),
            "followers_count": data.get("followersCount", 0),
            "posts_count": data.get("postsCount", 0),
            "avatar": data.get("avatar", ""),
            "banner": data.get("banner", ""),
            "source": "bluesky",
        }
    
    except Exception as exc:
        logger.debug(f"Bluesky profile failed: {exc}")
    return None


def mastodon_search(query: str, limit: int = 10, instance: str = "mastodon.social") -> Optional[Dict[str, Any]]:
    """Search Mastodon via public instance API (no auth required)."""
    try:
        resp = httpx.get(
            f"https://{instance}/api/v2/search",
            params={"q": query, "limit": limit, "type": "statuses"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        statuses = data.get("statuses", [])
        if not statuses:
            return None
        
        results = []
        for i, status in enumerate(statuses[:limit]):
            account = status.get("account", "")
            
            results.append({
                "title": f"Post by {account.get('display_name', account.get('username', ''))}",
                "url": status.get("url", ""),
                "description": re.sub(r'<[^>]+>', '', status.get("content", ""))[:300],
                "author": account.get("username", ""),
                "created_at": status.get("created_at", ""),
                "reblogs_count": status.get("reblogs_count", 0),
                "favourites_count": status.get("favourites_count", 0),
                "source": "mastodon",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Mastodon search failed: {exc}")
    return None


# ===========================================================================
# TIER B — Best-Effort Public Scraping (May Break)
# ===========================================================================

def linkedin_public_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Best-effort LinkedIn public profile discovery.
    
    Uses search engines to find public LinkedIn profiles.
    Does NOT scrape LinkedIn directly (blocked).
    """
    try:
        # Use search engine to find LinkedIn URLs
        search_query = f"site:linkedin.com/in {query}"
        
        # Use DuckDuckGo HTML
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": search_query},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_linkedin_urls(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"LinkedIn search failed: {exc}")
    return None


def _parse_linkedin_urls(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse LinkedIn URLs from search results."""
    results = []
    
    # Pattern for LinkedIn profile URLs
    pattern = re.compile(
        r'href="(https?://(?:www\.)?linkedin\.com/in/[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        if url and title:
            results.append({
                "title": title[:100],
                "url": url,
                "description": "LinkedIn public profile (metadata only)",
                "source": "linkedin",
                "confidence": 0.6,
                "position": len(results) + 1,
            })
    
    return results


def instagram_public_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Best-effort Instagram public profile discovery.
    
    Uses search engines to find public Instagram profiles.
    Does NOT scrape Instagram directly (heavily blocked).
    """
    try:
        search_query = f"site:instagram.com {query}"
        
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": search_query},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_instagram_urls(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Instagram search failed: {exc}")
    return None


def _parse_instagram_urls(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Instagram URLs from search results."""
    results = []
    
    pattern = re.compile(
        r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        if url and title:
            results.append({
                "title": title[:100],
                "url": url,
                "description": "Instagram public profile (metadata only)",
                "source": "instagram",
                "confidence": 0.5,
                "position": len(results) + 1,
            })
    
    return results


def tiktok_public_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Best-effort TikTok public video discovery.
    
    Uses search engines to find public TikTok videos.
    Does NOT scrape TikTok directly (blocked).
    """
    try:
        search_query = f"site:tiktok.com {query}"
        
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": search_query},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_tiktok_urls(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"TikTok search failed: {exc}")
    return None


def _parse_tiktok_urls(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse TikTok URLs from search results."""
    results = []
    
    pattern = re.compile(
        r'href="(https?://(?:www\.)?tiktok\.com/@[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        if url and title:
            results.append({
                "title": title[:100],
                "url": url,
                "description": "TikTok public video (metadata only)",
                "source": "tiktok",
                "confidence": 0.5,
                "position": len(results) + 1,
            })
    
    return results


def x_public_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Best-effort X/Twitter public post discovery.
    
    Uses search engines to find public X posts.
    Does NOT use X API (requires auth).
    """
    try:
        search_query = f"site:x.com {query}"
        
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": search_query},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_x_urls(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"X search failed: {exc}")
    return None


def _parse_x_urls(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse X/Twitter URLs from search results."""
    results = []
    
    pattern = re.compile(
        r'href="(https?://(?:www\.)?(?:x|twitter)\.com/[^"]+/status/[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        if url and title:
            results.append({
                "title": title[:100],
                "url": url,
                "description": "X/Twitter public post (metadata only)",
                "source": "x",
                "confidence": 0.5,
                "position": len(results) + 1,
            })
    
    return results


# ===========================================================================
# TIER C — Optional User Connectors (Official APIs with Keys)
# ===========================================================================

def linkedin_api_search(query: str, limit: int = 10, access_token: str = None) -> Optional[Dict[str, Any]]:
    """Search LinkedIn via official API (requires access token).
    
    This is a Tier C connector — only works if user provides credentials.
    """
    if not access_token:
        return None
    
    try:
        resp = httpx.get(
            "https://api.linkedin.com/v2/people",
            params={"q": "keywords", "keywords": query, "count": limit},
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": ua_rotator.get(),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        elements = data.get("elements", [])
        if not elements:
            return None
        
        results = []
        for i, person in enumerate(elements[:limit]):
            results.append({
                "title": person.get("firstName", "") + " " + person.get("lastName", ""),
                "url": person.get("vanityName", ""),
                "description": person.get("headline", ""),
                "source": "linkedin_api",
                "confidence": 0.95,
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"LinkedIn API search failed: {exc}")
    return None


def instagram_api_search(query: str, limit: int = 10, access_token: str = None) -> Optional[Dict[str, Any]]:
    """Search Instagram via official API (requires access token).
    
    This is a Tier C connector — only works if user provides credentials.
    """
    if not access_token:
        return None
    
    try:
        resp = httpx.get(
            "https://graph.instagram.com/me/media",
            params={"fields": "id,caption,media_url,permalink", "limit": limit, "access_token": access_token},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        media = data.get("data", [])
        if not media:
            return None
        
        results = []
        for i, item in enumerate(media[:limit]):
            results.append({
                "title": item.get("caption", "")[:100],
                "url": item.get("permalink", ""),
                "description": item.get("caption", "")[:300],
                "source": "instagram_api",
                "confidence": 0.95,
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Instagram API search failed: {exc}")
    return None


# ===========================================================================
# Source Registry
# ===========================================================================

def get_source_tiers() -> Dict[str, Any]:
    """Get three-tier source architecture."""
    return {
        "tier_a": {
            "name": "Official Public APIs",
            "description": "Genuinely free, no auth required",
            "sources": [
                "bluesky", "mastodon", "github", "hackernews", "lemmy",
                "wikipedia", "wikidata", "arxiv", "openalex", "crossref",
                "rss", "sitemap", "searxng", "ddgs", "jina-ddg",
            ],
            "reliability": "high",
        },
        "tier_b": {
            "name": "Best-Effort Public Scraping",
            "description": "May break, rate-limited, metadata only",
            "sources": [
                "linkedin", "instagram", "tiktok", "x",
            ],
            "reliability": "low",
        },
        "tier_c": {
            "name": "Optional User Connectors",
            "description": "Official APIs with user-provided keys",
            "sources": [
                "linkedin_api", "instagram_api", "twitter_api", "youtube_api",
            ],
            "reliability": "high (with credentials)",
        },
    }
