# -*- coding: utf-8 -*-
"""Agent Search Lite — Knowledge Base & Media Backends.

OpenStreetMap, Wikidata, GeoNames, DBpedia, RSS, Wayback Machine.

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

_OSM_API = "https://nominatim.openstreetmap.org"
_WIKIDATA_API = "https://www.wikidata.org/w/api.php"
_DBPEDIA_API = "https://dbpedia.org/sparql"
_GEONAMES_API = "http://api.geonames.org"
_WAYBACK_API = "https://archive.org/wayback"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.0; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# OpenStreetMap (Nominatim)
# ---------------------------------------------------------------------------

def osm_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search OpenStreetMap for locations.
    
    Free API, no key required (rate limited).
    """
    try:
        resp = httpx.get(
            f"{_OSM_API}/search",
            params={
                "q": query,
                "format": "json",
                "limit": limit,
                "addressdetails": 1,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data:
            return None
        
        results = []
        for i, place in enumerate(data[:limit]):
            display_name = place.get("display_name", "")
            address = place.get("address", {})
            
            results.append({
                "title": display_name.split(",")[0] if display_name else "",
                "url": f"https://www.openstreetmap.org/?mlat={place.get('lat')}&mlon={place.get('lon')}",
                "description": display_name,
                "lat": place.get("lat", ""),
                "lon": place.get("lon", ""),
                "type": place.get("type", ""),
                "source": "openstreetmap",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("OSM search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Wikidata
# ---------------------------------------------------------------------------

def wikidata_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Wikidata for structured data.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            _WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "format": "json",
                "limit": limit,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        search_results = data.get("search", [])
        if not search_results:
            return None
        
        results = []
        for i, entity in enumerate(search_results[:limit]):
            results.append({
                "title": entity.get("label", ""),
                "url": entity.get("concepturi", ""),
                "description": entity.get("description", ""),
                "id": entity.get("id", ""),
                "source": "wikidata",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Wikidata search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# GeoNames
# ---------------------------------------------------------------------------

def geonames_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search GeoNames for geographic names.
    
    Free API, username required (use 'demo' for testing).
    """
    try:
        resp = httpx.get(
            f"{_GEONAMES_API}/searchJSON",
            params={
                "q": query,
                "maxRows": limit,
                "username": "demo",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        places = data.get("geonames", [])
        if not places:
            return None
        
        results = []
        for i, place in enumerate(places[:limit]):
            results.append({
                "title": place.get("name", ""),
                "url": f"https://www.geonames.org/{place.get('geonameId', '')}",
                "description": f"{place.get('adminName1', '')}, {place.get('countryName', '')}",
                "lat": place.get("lat", ""),
                "lon": place.get("lng", ""),
                "population": place.get("population", 0),
                "source": "geonames",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("GeoNames search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# DBpedia
# ---------------------------------------------------------------------------

def dbpedia_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search DBpedia for structured data.
    
    Free SPARQL endpoint, no key required.
    """
    try:
        sparql_query = f"""
        SELECT ?resource ?label ?abstract WHERE {{
            ?resource rdfs:label ?label .
            ?resource dbo:abstract ?abstract .
            FILTER(CONTAINS(LCASE(?label), LCASE("{query}")))
            FILTER(LANG(?abstract) = "en")
        }}
        LIMIT {limit}
        """
        
        resp = httpx.get(
            _DBPEDIA_API,
            params={"query": sparql_query, "format": "json"},
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        
        results = []
        for i, binding in enumerate(bindings[:limit]):
            results.append({
                "title": binding.get("label", {}).get("value", ""),
                "url": binding.get("resource", {}).get("value", ""),
                "description": binding.get("abstract", {}).get("value", "")[:300],
                "source": "dbpedia",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("DBpedia search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# RSS Feed Reader
# ---------------------------------------------------------------------------

def rss_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search RSS feeds for news.
    
    Searches popular news RSS feeds.
    """
    try:
        import feedparser
        
        # Popular news RSS feeds
        feeds = [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.reuters.com/reuters/topNews",
            "https://feeds.npr.org/1001/rss.xml",
            "https://www.aljazeera.com/xml/rss/all.xml",
        ]
        
        all_entries = []
        
        for feed_url in feeds[:3]:  # Limit feeds to avoid rate limiting
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    if query.lower() in entry.get("title", "").lower() or \
                       query.lower() in entry.get("summary", "").lower():
                        all_entries.append({
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "description": entry.get("summary", "")[:300],
                            "published": entry.get("published", ""),
                            "source": "rss",
                            "position": len(all_entries) + 1,
                        })
            except Exception:
                continue
        
        if all_entries:
            return {"success": True, "data": {"web": all_entries[:limit]}}
            
    except ImportError:
        logger.debug("feedparser not installed")
    except Exception as exc:
        logger.debug("RSS search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# Wayback Machine
# ---------------------------------------------------------------------------

def wayback_search(url: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Wayback Machine for archived versions of a URL.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_WAYBACK_API}/available",
            params={"url": url},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        snapshots = data.get("archived_snapshots", {})
        closest = snapshots.get("closest", {})
        
        if closest:
            return {
                "success": True,
                "data": {
                    "web": [{
                        "title": f"Archived version of {url}",
                        "url": closest.get("url", ""),
                        "timestamp": closest.get("timestamp", ""),
                        "status": closest.get("status", ""),
                        "source": "wayback",
                        "position": 1,
                    }]
                },
            }
            
    except Exception as exc:
        logger.debug("Wayback search failed: %s", exc)
    
    return None
