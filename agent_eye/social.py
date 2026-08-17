# -*- coding: utf-8 -*-
"""Agent Search Lite — Lemmy and Stack Overflow backends.

Lemmy: Reddit replacement (free, open-source, no API key)
Stack Overflow: Programming Q&A (free, no key for read-only)

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

_LEMMY_INSTANCES = [
    "https://lemmy.world",
    "https://lemmy.ml",
    "https://sh.itjust.works",
    "https://lemmy.dbzer0.com",
]

_STACKOVERFLOW_API = "https://api.stackexchange.com/2.3"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/3.1; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# Lemmy Backend
# ---------------------------------------------------------------------------

def lemmy_search(query: str, limit: int = 5, instance: str = None) -> Optional[Dict[str, Any]]:
    """Search Lemmy for community discussions.
    
    Lemmy is a free, open-source Reddit alternative.
    No API key required. Searches across multiple instances.
    """
    instances = [instance] if instance else _LEMMY_INSTANCES
    
    for inst in instances:
        try:
            resp = httpx.get(
                f"{inst}/api/v3/search",
                params={
                    "q": query,
                    "type": "Posts",
                    "sort": "TopAll",
                    "limit": limit,
                },
                headers={"User-Agent": _UA},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            
            posts = data.get("posts", [])
            if not posts:
                continue
            
            results = []
            for i, post in enumerate(posts[:limit]):
                post_data = post.get("post", {})
                creator = post.get("creator", {})
                community = post.get("community", {})
                
                results.append({
                    "title": post_data.get("name", ""),
                    "url": post_data.get("url") or f"{inst}/post/{post_data.get('id', '')}",
                    "description": _clean_apub_content(post_data.get("body", ""))[:300],
                    "author": creator.get("name", ""),
                    "community": community.get("name", ""),
                    "score": post_data.get("score", 0),
                    "comments": post_data.get("comments", 0),
                    "source": "lemmy",
                    "position": len(results) + 1,
                })
            
            if results:
                return {"success": True, "data": {"web": results}}
                
        except httpx.HTTPStatusError as exc:
            logger.debug("Lemmy %s HTTP error: %s", inst, exc)
        except Exception as exc:
            logger.debug("Lemmy %s search failed: %s", inst, exc)
    
    return None


def lemmy_get_community_posts(community: str, instance: str = "lemmy.world", limit: int = 5) -> Optional[Dict[str, Any]]:
    """Get posts from a specific Lemmy community."""
    try:
        # First resolve community ID
        resp = httpx.get(
            f"{instance}/api/v3/community",
            params={"name": community},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        community_id = data.get("community_view", {}).get("community", {}).get("id")
        if not community_id:
            return None
        
        # Get posts
        resp = httpx.get(
            f"{instance}/api/v3/post/list",
            params={
                "community_id": community_id,
                "sort": "TopAll",
                "limit": limit,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        posts = data.get("posts", [])
        results = []
        for post in posts[:limit]:
            post_data = post.get("post", {})
            results.append({
                "title": post_data.get("name", ""),
                "url": post_data.get("url") or f"{instance}/post/{post_data.get('id', '')}",
                "description": _clean_apub_content(post_data.get("body", ""))[:300],
                "score": post_data.get("score", 0),
                "comments": post_data.get("comments", 0),
                "source": "lemmy",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Lemmy community posts failed: %s", exc)
        return None


def _clean_apub_content(content: str) -> str:
    """Clean ActivityPub/Lemmy content (remove markdown, links, etc.)."""
    if not content:
        return ""
    # Remove markdown links
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    # Remove markdown formatting
    content = re.sub(r'[*_~`]', '', content)
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    # Clean whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    return content


# ---------------------------------------------------------------------------
# Stack Overflow Backend
# ---------------------------------------------------------------------------

def stackoverflow_search(query: str, limit: int = 5, tagged: str = None) -> Optional[Dict[str, Any]]:
    """Search Stack Overflow for programming Q&A.
    
    Uses the Stack Exchange API (free, no key required for read-only).
    Returns questions with answers, votes, and tags.
    """
    try:
        params = {
            "order": "desc",
            "sort": "relevance",
            "intitle": query,
            "site": "stackoverflow",
            "pagesize": limit,
            "filter": "withbody",
        }
        if tagged:
            params["tagged"] = tagged
        
        resp = httpx.get(
            f"{_STACKOVERFLOW_API}/search",
            params=params,
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get("items", [])
        if not items:
            return None
        
        results = []
        for i, item in enumerate(items[:limit]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": _clean_html(item.get("body", ""))[:300],
                "author": item.get("owner", {}).get("display_name", ""),
                "score": item.get("score", 0),
                "answers": item.get("answer_count", 0),
                "tags": ", ".join(item.get("tags", [])[:3]),
                "is_answered": item.get("is_answered", False),
                "source": "stackoverflow",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except httpx.HTTPStatusError as exc:
        logger.debug("StackOverflow HTTP error: %s", exc)
    except Exception as exc:
        logger.debug("StackOverflow search failed: %s", exc)
    
    return None


def stackoverflow_get_question(question_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific Stack Overflow question with answers."""
    try:
        resp = httpx.get(
            f"{_STACKOVERFLOW_API}/questions/{question_id}",
            params={
                "order": "desc",
                "sort": "votes",
                "site": "stackoverflow",
                "filter": "withbody",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get("items", [])
        if not items:
            return None
        
        question = items[0]
        return {
            "title": question.get("title", ""),
            "body": _clean_html(question.get("body", "")),
            "url": question.get("link", ""),
            "score": question.get("score", 0),
            "answers": question.get("answer_count", 0),
        }
        
    except Exception as exc:
        logger.debug("StackOverflow get question failed: %s", exc)
        return None


def _clean_html(html: str) -> str:
    """Remove HTML tags from content."""
    if not html:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode entities
    text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
