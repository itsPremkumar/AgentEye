# -*- coding: utf-8 -*-
"""Agent Search Lite — E-commerce, Government, Jobs, Weather, Patents.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DATAGOV_API = "https://api.data.gov"
WORLDBANK_API = "https://api.worldbank.org/v2"
UN_DATA_API = "https://data.un.org/WS/REST"
WEATHER_API = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_API = "https://api.openweathermap.org/data/2.5"
NWS_API = "https://api.weather.gov"
PATENTS_API = "https://api.patentsview.org"
USPTO_API = "https://tmsearch.uspto.gov"
INDEED_API = "https://api.indeed.com/ads/apisearch"
AMAZON_PAAPI = "https://webservices.amazon.com/paapi5"
EBAY_API = "https://api.ebay.com/buy/browse/v1"
OPENCORPORATES_API = "https://api.opencorporates.com/v0.4"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.1; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# US Government Data (data.gov)
# ---------------------------------------------------------------------------

def datagov_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search US government open data."""
    try:
        resp = httpx.get(
            "https://catalog.data.gov/api/3/action/package_search",
            params={"q": query, "rows": limit},
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results_list = data.get("result", {}).get("results", [])
        if not results_list:
            return None
        
        results = []
        for item in results_list[:limit]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("notes", "")[:300],
                "organization": item.get("organization", {}).get("title", ""),
                "source": "data.gov",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("data.gov search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# World Bank Open Data
# ---------------------------------------------------------------------------

def worldbank_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search World Bank development data."""
    try:
        # Search indicators
        resp = httpx.get(
            f"{WORLDBANK_API}/indicator",
            params={"format": "json", "per_page": limit, "source": "2"},
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        indicators = data[1] if len(data) > 1 else []
        if not indicators:
            return None
        
        results = []
        for item in indicators[:limit]:
            name = item.get("name", "")
            if query.lower() in name.lower():
                results.append({
                    "title": name,
                    "url": f"https://data.worldbank.org/indicator/{item.get('id', '')}",
                    "description": item.get("sourceNote", "")[:300],
                    "source": "worldbank",
                    "position": len(results) + 1,
                })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("World Bank search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# UN Data
# ---------------------------------------------------------------------------

def undata_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search UN sustainable development data."""
    try:
        resp = httpx.get(
            "https://unstats.un.org/SDGAPI/v1/sdg/Target/List",
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data[:limit]:
            title = item.get("title", "")
            if query.lower() in title.lower():
                results.append({
                    "title": title,
                    "url": f"https://unstats.un.org/sdgs/report/2024/goal-{item.get('goal', '')}/",
                    "description": item.get("description", "")[:300],
                    "source": "undata",
                    "position": len(results) + 1,
                })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("UN Data search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Weather (Open-Meteo - no API key required)
# ---------------------------------------------------------------------------

def weather_search(city: str, limit: int = 1) -> Optional[Dict[str, Any]]:
    """Search weather using Open-Meteo (free, no API key)."""
    try:
        # First geocode the city
        geo_resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        
        locations = geo_data.get("results", [])
        if not locations:
            return None
        
        loc = locations[0]
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        
        # Get weather data
        weather_resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
        
        current = weather_data.get("current_weather", {})
        
        return {
            "success": True,
            "data": {
                "web": [{
                    "title": f"Weather in {loc.get('name', city)}, {loc.get('country', '')}",
                    "url": f"https://open-meteo.com/en/docs",
                    "description": (
                        f"Temperature: {current.get('temperature', 'N/A')}°C, "
                        f"Wind: {current.get('windspeed', 'N/A')} km/h, "
                        f"Condition: {current.get('weathercode', 'N/A')}"
                    ),
                    "lat": lat,
                    "lon": lon,
                    "source": "weather",
                    "position": 1,
                }]
            },
        }
    except Exception as exc:
        logger.debug("Weather search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# US National Weather Service
# ---------------------------------------------------------------------------

def nws_search(lat: float, lon: float, limit: int = 1) -> Optional[Dict[str, Any]]:
    """Get weather from US NWS API (free, US only)."""
    try:
        resp = httpx.get(
            f"{NWS_API}/points/{lat},{lon}",
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        forecast_url = data.get("properties", {}).get("forecast")
        if not forecast_url:
            return None
        
        forecast_resp = httpx.get(forecast_url, headers={"User-Agent": _UA}, timeout=15)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        
        periods = forecast_data.get("properties", {}).get("periods", [])
        if not periods:
            return None
        
        results = []
        for period in periods[:limit]:
            results.append({
                "title": period.get("name", ""),
                "url": period.get("detailedForecast", ""),
                "description": period.get("detailedForecast", "")[:300],
                "temperature": period.get("temperature", ""),
                "source": "nws",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("NWS search failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Patents (PatentsView - US patents)
# ---------------------------------------------------------------------------

def patents_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search US patents via PatentsView API."""
    try:
        resp = httpx.get(
            f"{PATENTS_API}/patents/query",
            params={
                "q": f'{{"patent_title":"{query}"}}',
                "f": '["patent_number","patent_title","patent_date","patent_abstract"]',
                "o": f'{{"per_page":{limit}}}',
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        patents = data.get("patents", [])
        if not patents:
            return None
        
        results = []
        for patent in patents[:limit]:
            results.append({
                "title": patent.get("patent_title", ""),
                "url": f"https://patents.google.com/patent/US{patent.get('patent_number', '')}",
                "description": patent.get("patent_abstract", "")[:300],
                "date": patent.get("patent_date", ""),
                "source": "patents",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("Patents search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Google Patents (scraping alternative)
# ---------------------------------------------------------------------------

def google_patents_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Google Patents as fallback."""
    try:
        resp = httpx.get(
            "https://patents.google.com/xhr/query",
            params={"url": f"q={urllib.parse.quote(query)}", "exp": ""},
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results_list = data.get("results", {}).get("cluster", [])
        if not results_list:
            return None
        
        results = []
        for cluster in results_list[:limit]:
            result = cluster.get("result", [{}])[0] if cluster.get("result") else {}
            title = result.get("patent", {}).get("title", "")
            if title:
                results.append({
                    "title": title,
                    "url": f"https://patents.google.com/patent/{result.get('patent', {}).get('publication_number', '')}",
                    "description": result.get("patent", {}).get("abstract", "")[:300],
                    "source": "google_patents",
                    "position": len(results) + 1,
                })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("Google Patents search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Job Search (Adzuna - free tier)
# ---------------------------------------------------------------------------

def jobs_search(query: str, country: str = "us", limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search jobs via Adzuna API (free tier available)."""
    try:
        # Note: Adzuna requires app_id and app_key
        # For now, use a simple scraping approach
        resp = httpx.get(
            f"https://www.indeed.com/jobs",
            params={"q": query, "l": country},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        
        # Parse HTML for job listings
        html = resp.text
        results = _parse_indeed_jobs(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("Job search failed: %s", exc)
    return None


def _parse_indeed_jobs(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Indeed HTML for job listings."""
    import re
    
    results = []
    # Simple regex-based parsing
    job_pattern = re.compile(
        r'<h2 class="jobTitle[^"]*">.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<div class="job-snippet">(.*?)</div>',
        re.DOTALL
    )
    
    jobs = job_pattern.findall(html)
    
    for i, (url, title, snippet) in enumerate(jobs[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', ' ', snippet).strip()
        
        if title:
            results.append({
                "title": title[:100],
                "url": f"https://www.indeed.com{url}",
                "description": snippet[:200],
                "source": "jobs",
                "position": len(results) + 1,
            })
    
    return results


# ---------------------------------------------------------------------------
# OpenCorporates (company data)
# ---------------------------------------------------------------------------

def opencorporates_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search OpenCorporates for company data."""
    try:
        resp = httpx.get(
            f"{OPENCORPORATES_API}/companies/search",
            params={"q": query, "per_page": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        companies = data.get("results", {}).get("companies", [])
        if not companies:
            return None
        
        results = []
        for company in companies[:limit]:
            c = company.get("company", {})
            results.append({
                "title": c.get("name", ""),
                "url": c.get("company_url", ""),
                "description": f"{c.get('jurisdiction_code', '')} - {c.get('company_type', '')}",
                "source": "opencorporates",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("OpenCorporates search failed: %s", exc)
    return None
