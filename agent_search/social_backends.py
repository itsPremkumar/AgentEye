# -*- coding: utf-8 -*-
"""Agent Search Lite — Social Media Backends.

Twitter/Nitter, YouTube/Invidious, LinkedIn, Mastodon, Telegram.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
]

_INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
    "https://invidious.nerdvpn.de",
    "https://inv.nadeko.net",
    "https://invidious.jing.rocks",
]

_MASTODON_INSTANCES = [
    "https://mastodon.social",
    "https://fosstodon.org",
    "https://hachyderm.io",
    "https://tech.lgbt",
]

_TELEGRAM_BASE = "https://t.me"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.0; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# Twitter/X via Nitter
# ---------------------------------------------------------------------------

def twitter_search(query: str, limit: int = 5, instance: str = None) -> Optional[Dict[str, Any]]:
    """Search Twitter/X via Nitter instances (free, no API key)."""
    instances = [instance] if instance else _NITTER_INSTANCES
    
    for inst in instances:
        try:
            resp = httpx.get(
                f"{inst}/search",
                params={"f": "tweets", "q": query, "near": ""},
                headers={"User-Agent": _UA},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
            
            # Parse HTML for tweets
            html = resp.text
            tweets = _parse_nitter_tweets(html, limit)
            
            if tweets:
                return {"success": True, "data": {"web": tweets}}
                
        except Exception as exc:
            logger.debug("Nitter %s failed: %s", inst, exc)
    
    return None


def _parse_nitter_tweets(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Nitter HTML for tweets."""
    results = []
    
    # Simple regex-based parsing for tweet content
    tweet_pattern = re.compile(
        r'<div class="tweet-content[^"]*".*?<div class="tweet-body">(.*?)</div>',
        re.DOTALL
    )
    
    tweets = tweet_pattern.findall(html)
    
    for i, tweet_html in enumerate(tweets[:limit]):
        # Clean HTML
        text = re.sub(r'<[^>]+>', ' ', tweet_html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:
            results.append({
                "title": text[:100] + "..." if len(text) > 100 else text,
                "url": "",
                "description": text,
                "source": "twitter",
                "position": len(results) + 1,
            })
    
    return results


# ---------------------------------------------------------------------------
# YouTube via Invidious
# ---------------------------------------------------------------------------

def youtube_search(query: str, limit: int = 5, instance: str = None) -> Optional[Dict[str, Any]]:
    """Search YouTube via Invidious instances (free, no API key)."""
    instances = [instance] if instance else _INVIDIOUS_INSTANCES
    
    for inst in instances:
        try:
            resp = httpx.get(
                f"{inst}/api/v1/search",
                params={"q": query, "type": "video"},
                headers={"User-Agent": _UA},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                continue
            
            results = []
            for i, video in enumerate(data[:limit]):
                video_id = video.get("videoId", "")
                results.append({
                    "title": video.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "description": video.get("description", "")[:300],
                    "author": video.get("author", ""),
                    "duration": video.get("lengthSeconds", 0),
                    "views": video.get("viewCount", 0),
                    "source": "youtube",
                    "position": len(results) + 1,
                })
            
            if results:
                return {"success": True, "data": {"web": results}}
                
        except Exception as exc:
            logger.debug("Invidious %s failed: %s", inst, exc)
    
    return None


def youtube_get_video_info(video_id: str, instance: str = None) -> Optional[Dict[str, Any]]:
    """Get YouTube video metadata via Invidious."""
    instances = [instance] if instance else _INVIDIOUS_INSTANCES
    
    for inst in instances:
        try:
            resp = httpx.get(
                f"{inst}/api/v1/videos/{video_id}",
                headers={"User-Agent": _UA},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "author": data.get("author", ""),
                "duration": data.get("lengthSeconds", 0),
                "views": data.get("viewCount", 0),
                "likes": data.get("likeCount", 0),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
            
        except Exception as exc:
            logger.debug("Invidious video info failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# LinkedIn (public scraping)
# ---------------------------------------------------------------------------

def linkedin_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search LinkedIn public posts (limited, no API key)."""
    try:
        # LinkedIn public search is limited without API key
        # This searches for public posts via Google-style search
        resp = httpx.get(
            "https://www.linkedin.com/pub/dir/+/+",
            params={"trk": "people-guest_people-search-bar_search-submit"},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        
        # LinkedIn requires authentication for most searches
        # Return empty result for now
        logger.debug("LinkedIn search requires authentication")
        return None
        
    except Exception as exc:
        logger.debug("LinkedIn search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Mastodon
# ---------------------------------------------------------------------------

def mastodon_search(query: str, limit: int = 5, instance: str = None) -> Optional[Dict[str, Any]]:
    """Search Mastodon for public posts (free, no API key)."""
    instances = [instance] if instance else _MASTODON_INSTANCES
    
    for inst in instances:
        try:
            resp = httpx.get(
                f"{inst}/api/v2/search",
                params={
                    "q": query,
                    "type": "statuses",
                    "limit": limit,
                    "resolve": "false",
                },
                headers={"User-Agent": _UA},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            
            statuses = data.get("statuses", [])
            if not statuses:
                continue
            
            results = []
            for i, status in enumerate(statuses[:limit]):
                account = status.get("account", {})
                content = _clean_mastodon_content(status.get("content", ""))
                
                results.append({
                    "title": content[:100] + "..." if len(content) > 100 else content,
                    "url": status.get("url", ""),
                    "description": content,
                    "author": account.get("display_name", ""),
                    "reblogs": status.get("reblogs_count", 0),
                    "favourites": status.get("favourites_count", 0),
                    "source": "mastodon",
                    "position": len(results) + 1,
                })
            
            if results:
                return {"success": True, "data": {"web": results}}
                
        except Exception as exc:
            logger.debug("Mastodon %s failed: %s", inst, exc)
    
    return None


def _clean_mastodon_content(html: str) -> str:
    """Clean Mastodon HTML content."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---------------------------------------------------------------------------
# Telegram (public channels)
# ---------------------------------------------------------------------------

def telegram_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Telegram public channels (limited without API key)."""
    try:
        # Telegram public search is limited
        # This is a placeholder for future implementation
        logger.debug("Telegram search requires API key for full functionality")
        return None
        
    except Exception as exc:
        logger.debug("Telegram search failed: %s", exc)
        return None


def telegram_get_channel_posts(channel: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Get posts from a public Telegram channel."""
    try:
        resp = httpx.get(
            f"{_TEGRAM_BASE}/{channel}",
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_telegram_posts(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Telegram channel posts failed: %s", exc)
    
    return None


def _parse_telegram_posts(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Telegram channel HTML for posts."""
    results = []
    
    # Simple regex-based parsing
    post_pattern = re.compile(
        r'<div class="tgme_widget_message_text[^"]*">(.*?)</div>',
        re.DOTALL
    )
    
    posts = post_pattern.findall(html)
    
    for i, post_html in enumerate(posts[:limit]):
        text = re.sub(r'<[^>]+>', ' ', post_html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:
            results.append({
                "title": text[:100] + "..." if len(text) > 100 else text,
                "url": "",
                "description": text,
                "source": "telegram",
                "position": len(results) + 1,
            })
    
    return results
