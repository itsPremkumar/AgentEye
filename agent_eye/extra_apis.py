# -*- coding: utf-8 -*-
"""AgentLens — Additional Free Public APIs.

More package registries, news APIs, NASA, USGS, Datamuse.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)


# ===========================================================================
# Package Registries
# ===========================================================================

def rubygems_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search RubyGems for Ruby packages."""
    try:
        resp = httpx.get(
            "https://rubygems.org/api/v1/search.json",
            params={"query": query, "limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        gems = resp.json()
        
        if not gems:
            return None
        
        results = []
        for i, gem in enumerate(gems[:limit]):
            results.append({
                "title": gem.get("name", ""),
                "url": gem.get("homepage_uri", f"https://rubygems.org/gems/{gem.get('name', '')}"),
                "description": gem.get("info", "")[:300],
                "version": gem.get("version", ""),
                "downloads": gem.get("downloads", 0),
                "source": "rubygems",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"RubyGems search failed: {exc}")
    return None


def nuget_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search NuGet for .NET packages."""
    try:
        resp = httpx.get(
            "https://api-v2v3search-0.nuget.org/query",
            params={"q": query, "take": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        packages = data.get("data", [])
        if not packages:
            return None
        
        results = []
        for i, pkg in enumerate(packages[:limit]):
            results.append({
                "title": pkg.get("id", ""),
                "url": pkg.get("projectUrl", f"https://www.nuget.org/packages/{pkg.get('id', '')}"),
                "description": pkg.get("description", "")[:300],
                "version": pkg.get("version", ""),
                "totalDownloads": pkg.get("totalDownloads", 0),
                "source": "nuget",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"NuGet search failed: {exc}")
    return None


def maven_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Maven Central for Java packages."""
    try:
        resp = httpx.get(
            "https://search.maven.org/solrsearch/select",
            params={"q": query, "rows": limit, "wt": "json"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        docs = data.get("response", {}).get("docs", [])
        if not docs:
            return None
        
        results = []
        for i, doc in enumerate(docs[:limit]):
            results.append({
                "title": f"{doc.get('g', '')}:{doc.get('a', '')}",
                "url": f"https://search.maven.org/artifact/{doc.get('g', '')}/{doc.get('a', '')}",
                "description": doc.get("desc", "")[:300] if doc.get("desc") else f"v{doc.get('v', '')}",
                "version": doc.get("v", ""),
                "packaging": doc.get("p", ""),
                "source": "maven",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Maven search failed: {exc}")
    return None


def cocoapods_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search CocoaPods for iOS/macOS packages."""
    try:
        resp = httpx.get(
            "https://trunk.cocoapods.org/api/v1/pods",
            params={"query": query, "limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        pods = data.get("data", [])
        if not pods:
            return None
        
        results = []
        for i, pod in enumerate(pods[:limit]):
            results.append({
                "title": pod.get("name", ""),
                "url": pod.get("homepage", f"https://cocoapods.org/pods/{pod.get('name', '')}"),
                "description": pod.get("summary", "")[:300],
                "version": pod.get("version", ""),
                "source": "cocoapods",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"CocoaPods search failed: {exc}")
    return None


def pubdev_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Pub.dev for Dart/Flutter packages."""
    try:
        resp = httpx.get(
            "https://pub.dev/api/search",
            params={"q": query, "page": 1},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        packages = data.get("packages", [])
        if not packages:
            return None
        
        results = []
        for i, pkg in enumerate(packages[:limit]):
            results.append({
                "title": pkg.get("package", ""),
                "url": f"https://pub.dev/packages/{pkg.get('package', '')}",
                "description": pkg.get("latest", {}).get("pubspec", {}).get("description", "")[:300],
                "version": pkg.get("latest", {}).get("version", ""),
                "source": "pubdev",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Pub.dev search failed: {exc}")
    return None


# ===========================================================================
# News APIs
# ===========================================================================

def newsapi_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search news via NewsAPI (requires API key for production).
    
    Note: NewsAPI free tier requires registration.
    This is a best-effort connector.
    """
    # NewsAPI requires API key - return None for now
    return None


def gnews_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search news via GNews (requires API key).
    
    Note: GNews free tier requires registration.
    """
    return None


def currents_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search news via Currents API (requires API key)."""
    return None


# ===========================================================================
# NASA APIs
# ===========================================================================

def nasa_apod() -> Optional[Dict[str, Any]]:
    """Get NASA Astronomy Picture of the Day."""
    try:
        resp = httpx.get(
            "https://api.nasa.gov/planetary/apod",
            params={"api_key": "DEMO_KEY", "count": 1},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if isinstance(data, list):
            data = data[0] if data else {}
        
        return {
            "title": data.get("title", ""),
            "url": data.get("url", ""),
            "hdurl": data.get("hdurl", ""),
            "description": data.get("explanation", ""),
            "date": data.get("date", ""),
            "media_type": data.get("media_type", ""),
            "source": "nasa_apod",
        }
    
    except Exception as exc:
        logger.debug(f"NASA APOD failed: {exc}")
    return None


def nasa_mars_photos(rover: str = "curiosity", sol: int = 1000, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Get NASA Mars rover photos."""
    try:
        resp = httpx.get(
            f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos",
            params={"sol": sol, "api_key": "DEMO_KEY"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        photos = data.get("photos", [])
        if not photos:
            return None
        
        results = []
        for i, photo in enumerate(photos[:limit]):
            results.append({
                "title": f"{photo.get('rover', {}).get('name', '')} - {photo.get('camera', {}).get('full_name', '')}",
                "url": photo.get("img_src", ""),
                "description": f"Sol {photo.get('sol', '')} - Earth date: {photo.get('earth_date', '')}",
                "date": photo.get("earth_date", ""),
                "source": "nasa_mars",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"NASA Mars photos failed: {exc}")
    return None


def nasa_neo_feed(start_date: str = None, end_date: str = None) -> Optional[Dict[str, Any]]:
    """Get NASA Near Earth Objects feed."""
    try:
        from datetime import datetime, timedelta
        
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        resp = httpx.get(
            "https://api.nasa.gov/neo/rest/v1/feed",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "api_key": "DEMO_KEY",
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        neo_data = data.get("near_earth_objects", {})
        results = []
        
        for date, neos in neo_data.items():
            for neo in neos[:3]:
                results.append({
                    "title": neo.get("name", ""),
                    "url": neo.get("nasa_jpl_url", ""),
                    "description": f"Potentially hazardous: {neo.get('is_potentially_hazardous_asteroid', False)}",
                    "date": date,
                    "source": "nasa_neo",
                    "position": len(results) + 1,
                })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"NASA NEO feed failed: {exc}")
    return None


# ===========================================================================
# USGS Earthquake API
# ===========================================================================

def usgs_earthquakes(
    start_time: str = None,
    end_time: str = None,
    min_magnitude: float = 4.0,
    limit: int = 10,
) -> Optional[Dict[str, Any]]:
    """Get recent earthquakes from USGS."""
    try:
        from datetime import datetime, timedelta
        
        if not end_time:
            end_time = datetime.now().strftime("%Y-%m-%d")
        if not start_time:
            start_time = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        resp = httpx.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={
                "format": "geojson",
                "starttime": start_time,
                "endtime": end_time,
                "minmagnitude": min_magnitude,
                "limit": limit,
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        features = data.get("features", [])
        if not features:
            return None
        
        results = []
        for i, feature in enumerate(features[:limit]):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])
            
            results.append({
                "title": props.get("title", ""),
                "url": props.get("url", ""),
                "description": f"Magnitude: {props.get('mag', '')} - Depth: {coords[2]}km",
                "magnitude": props.get("mag", 0),
                "place": props.get("place", ""),
                "time": props.get("time", ""),
                "source": "usgs_earthquake",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"USGS earthquakes failed: {exc}")
    return None


def usgs_volcanoes(limit: int = 10) -> Optional[Dict[str, Any]]:
    """Get USGS volcano information."""
    try:
        resp = httpx.get(
            "https://volcanoes.usgs.gov/hans2/api/volcano",
            params={"format": "json", "limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        volcanoes = data.get("volcanoes", [])
        if not volcanoes:
            return None
        
        results = []
        for i, volcano in enumerate(volcanoes[:limit]):
            results.append({
                "title": volcano.get("volcano_name", ""),
                "url": f"https://volcanoes.usgs.gov/volcanoes/{volcano.get('volcano_name', '').replace(' ', '_').lower()}",
                "description": f"{volcano.get('primary_country', '')} - {volcano.get('volcano_type', '')}",
                "elevation": volcano.get("elevation", 0),
                "source": "usgs_volcano",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"USGS volcanoes failed: {exc}")
    return None


# ===========================================================================
# Datamuse API
# ===========================================================================

def datamuse_words(query: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
    """Search Datamuse for words matching criteria."""
    try:
        resp = httpx.get(
            "https://api.datamuse.com/words",
            params={"ml": query, "max": max_results},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        words = resp.json()
        
        if not words:
            return None
        
        results = []
        for i, word_data in enumerate(words[:max_results]):
            results.append({
                "title": word_data.get("word", ""),
                "url": f"https://www.dictionary.com/browse/{word_data.get('word', '')}",
                "description": f"Score: {word_data.get('score', 0)} - Frequency: {word_data.get('tags', [])}",
                "score": word_data.get("score", 0),
                "source": "datamuse",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Datamuse search failed: {exc}")
    return None


def datamuse_rhymes(word: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
    """Find rhymes for a word using Datamuse."""
    try:
        resp = httpx.get(
            "https://api.datamuse.com/words",
            params={"rel_rhy": word, "max": max_results},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        words = resp.json()
        
        if not words:
            return None
        
        results = []
        for i, word_data in enumerate(words[:max_results]):
            results.append({
                "title": word_data.get("word", ""),
                "url": f"https://www.rhymezone.com/r/rhyme.cgi?Word={word_data.get('word', '')}",
                "description": f"Rhymes with: {word} - Score: {word_data.get('score', 0)}",
                "score": word_data.get("score", 0),
                "source": "datamuse_rhyme",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Datamuse rhymes failed: {exc}")
    return None


def datamuse_synonyms(word: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
    """Find synonyms for a word using Datamuse."""
    try:
        resp = httpx.get(
            "https://api.datamuse.com/words",
            params={"rel_syn": word, "max": max_results},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        words = resp.json()
        
        if not words:
            return None
        
        results = []
        for i, word_data in enumerate(words[:max_results]):
            results.append({
                "title": word_data.get("word", ""),
                "url": f"https://www.thesaurus.com/browse/{word_data.get('word', '')}",
                "description": f"Synonym of: {word} - Score: {word_data.get('score', 0)}",
                "score": word_data.get("score", 0),
                "source": "datamuse_synonym",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"Datamuse synonyms failed: {exc}")
    return None


# ===========================================================================
# ConceptNet API
# ===========================================================================

def conceptnet_lookup(word: str, lang: str = "en", limit: int = 10) -> Optional[Dict[str, Any]]:
    """Look up a word in ConceptNet knowledge graph."""
    try:
        resp = httpx.get(
            f"http://api.conceptnet.io/c/{lang}/{word}",
            params={"limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        edges = data.get("edges", [])
        if not edges:
            return None
        
        results = []
        for i, edge in enumerate(edges[:limit]):
            start = edge.get("start", {})
            end = edge.get("end", {})
            rel = edge.get("rel", {})
            
            results.append({
                "title": f"{start.get('label', '')} → {end.get('label', '')}",
                "url": f"http://api.conceptnet.io{start.get('@id', '')}",
                "description": f"Relation: {rel.get('label', '')} - Weight: {edge.get('weight', 0):.2f}",
                "weight": edge.get("weight", 0),
                "source": "conceptnet",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug(f"ConceptNet lookup failed: {exc}")
    return None


# ===========================================================================
# WordNet (via NLTK or API)
# ===========================================================================

def wordnet_lookup(word: str) -> Optional[Dict[str, Any]]:
    """Look up a word in WordNet via NLTK."""
    try:
        from nltk.corpus import wordnet as wn
        
        synsets = wn.synsets(word)
        if not synsets:
            return None
        
        results = []
        for i, synset in enumerate(synsets[:10]):
            results.append({
                "title": synset.name(),
                "url": f"https://wordnet.princeton.edu/perl/webwn?s={word}",
                "description": synset.definition(),
                "pos": synset.pos(),
                "source": "wordnet",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except ImportError:
        logger.debug("NLTK not installed for WordNet lookup")
    except Exception as exc:
        logger.debug(f"WordNet lookup failed: {exc}")
    return None
