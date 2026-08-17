# -*- coding: utf-8 -*-
"""Agent Search Lite — Media & Entertainment Backends.

TMDB (movies/TV), Last.fm (music), OpenLibrary (books), IGDB (games).

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

TMDB_API = "https://api.themoviedb.org/3"
TMDB_PUBLIC = "https://www.themoviedb.org"
LASTFM_API = "https://ws.audioscrobbler.com/2.0"
OPENLIBRARY_API = "https://openlibrary.org"
IGDB_API = "https://api.igdb.com/v4"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.1; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# TMDB (The Movie Database) - public endpoints
# ---------------------------------------------------------------------------

def tmdb_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search TMDB for movies and TV shows (public, no key for basic search)."""
    try:
        # Use the public search endpoint
        resp = httpx.get(
            f"{TMDB_PUBLIC}/search",
            params={"query": query, "language": "en-US"},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        
        # Parse HTML for results
        html = resp.text
        results = _parse_tmdb_results(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("TMDB search failed: %s", exc)
    return None


def _parse_tmdb_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse TMDB HTML for movie/TV results."""
    import re
    
    results = []
    # Simple regex-based parsing
    card_pattern = re.compile(
        r'<div class="card[^"]*">.*?<a[^>]*href="(/movie/\d+|/tv/\d+)"[^>]*>.*?<img[^>]*alt="([^"]*)"[^>]*>.*?</a>',
        re.DOTALL
    )
    
    cards = card_pattern.findall(html)
    
    for i, (url, title) in enumerate(cards[:limit]):
        if title:
            media_type = "movie" if "/movie/" in url else "tv"
            results.append({
                "title": title,
                "url": f"{TMDB_PUBLIC}{url}",
                "description": f"{media_type.capitalize()} - {title}",
                "source": "tmdb",
                "position": len(results) + 1,
            })
    
    return results


# ---------------------------------------------------------------------------
# Last.fm - music search
# ---------------------------------------------------------------------------

def lastfm_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Last.fm for music (free, no key for basic search)."""
    try:
        resp = httpx.get(
            f"{LASTFM_API}/",
            params={
                "method": "track.search",
                "track": query,
                "format": "json",
                "limit": limit,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        tracks = data.get("results", {}).get("trackmatches", {}).get("track", [])
        if not tracks:
            return None
        
        results = []
        for track in tracks[:limit]:
            results.append({
                "title": track.get("name", ""),
                "url": track.get("url", ""),
                "description": f"Artist: {track.get('artist', '')} - Listeners: {track.get('listeners', 0)}",
                "source": "lastfm",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("Last.fm search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# OpenLibrary - book search
# ---------------------------------------------------------------------------

def openlibrary_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search OpenLibrary for books (free, no key required)."""
    try:
        resp = httpx.get(
            f"{OPENLIBRARY_API}/search.json",
            params={"q": query, "limit": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        docs = data.get("docs", [])
        if not docs:
            return None
        
        results = []
        for doc in docs[:limit]:
            title = doc.get("title", "")
            authors = ", ".join(doc.get("author_name", [])[:3])
            
            results.append({
                "title": title,
                "url": f"{OPENLIBRARY_API}{doc.get('key', '')}",
                "description": f"Author: {authors} - Year: {doc.get('first_publish_year', 'N/A')}",
                "source": "openlibrary",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("OpenLibrary search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# IGDB (Internet Game Database) - requires API key
# ---------------------------------------------------------------------------

def igdb_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search IGDB for video games (requires API key)."""
    try:
        # IGDB requires Twitch OAuth token
        # This is a placeholder for future implementation
        logger.debug("IGDB search requires API key")
        return None
    except Exception as exc:
        logger.debug("IGDB search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# BoardGameAtlas - board game search
# ---------------------------------------------------------------------------

def boardgameatlas_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search BoardGameAtlas for board games (free tier available)."""
    try:
        resp = httpx.get(
            "https://api.boardgameatlas.com/api/search",
            params={"name": query, "limit": limit, "client_id": "JW2hqz9v7w"},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        games = data.get("games", [])
        if not games:
            return None
        
        results = []
        for game in games[:limit]:
            results.append({
                "title": game.get("name", ""),
                "url": game.get("url", ""),
                "description": f"{game.get('year_published', 'N/A')} - {game.get('primary_publisher', {}).get('name', 'N/A')}",
                "source": "boardgameatlas",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("BoardGameAtlas search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# AniList - anime/manga search
# ---------------------------------------------------------------------------

def anilist_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search AniList for anime and manga (free GraphQL API)."""
    try:
        graphql_query = """
        query ($search: String, $perPage: Int) {
            Page(perPage: $perPage) {
                media(search: $search, type: ANIME) {
                    id
                    title { romaji english }
                    description
                    episodes
                    status
                }
            }
        }
        """
        
        resp = httpx.post(
            "https://graphql.anilist.co",
            json={
                "query": graphql_query,
                "variables": {"search": query, "perPage": limit},
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        media_list = data.get("data", {}).get("Page", {}).get("media", [])
        if not media_list:
            return None
        
        results = []
        for media in media_list[:limit]:
            title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "")
            description = media.get("description", "")[:300] if media.get("description") else ""
            
            results.append({
                "title": title,
                "url": f"https://anilist.co/anime/{media.get('id', '')}",
                "description": description,
                "episodes": media.get("episodes", "N/A"),
                "source": "anilist",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("AniList search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# MyAnimeList (via Jikan API) - anime/manga search
# ---------------------------------------------------------------------------

def mal_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search MyAnimeList via Jikan API (free, no key required)."""
    try:
        resp = httpx.get(
            "https://api.jikan.moe/v4/anime",
            params={"q": query, "limit": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        anime_list = data.get("data", [])
        if not anime_list:
            return None
        
        results = []
        for anime in anime_list[:limit]:
            title = anime.get("title", "")
            synopsis = anime.get("synopsis", "")[:300] if anime.get("synopsis") else ""
            
            results.append({
                "title": title,
                "url": anime.get("url", ""),
                "description": synopsis,
                "episodes": anime.get("episodes", "N/A"),
                "score": anime.get("score", "N/A"),
                "source": "myanimelist",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("MAL search failed: %s", exc)
    return None
