# -*- coding: utf-8 -*-
"""Agent Search Lite — Sitemap.xml & Robots.txt Parser.

Parses sitemap.xml and robots.txt to discover website structure,
URLs, and crawl rules.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Robots.txt Parser
# ---------------------------------------------------------------------------

def parse_robots_txt(base_url: str, timeout: int = 15) -> Dict[str, Any]:
    """Parse robots.txt from a website.
    
    Returns:
        {
            "sitemaps": ["https://example.com/sitemap.xml"],
            "agents": {
                "*": {
                    "allow": ["/public/"],
                    "disallow": ["/admin/", "/private/"]
                }
            },
            "crawl_delay": 1,
            "host": "example.com"
        }
    """
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        resp = httpx.get(
            robots_url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
            follow_redirects=True,
        )
        
        if resp.status_code != 200:
            return {"sitemaps": [], "agents": {}, "raw": ""}
        
        text = resp.text
        return _parse_robots_content(text)
        
    except Exception as exc:
        logger.debug(f"Failed to fetch robots.txt for {base_url}: {exc}")
        return {"sitemaps": [], "agents": {}, "raw": ""}


def _parse_robots_content(text: str) -> Dict[str, Any]:
    """Parse robots.txt content."""
    result = {
        "sitemaps": [],
        "agents": {},
        "crawl_delay": None,
        "host": None,
        "raw": text,
    }
    
    current_agent = None
    
    for line in text.split("\n"):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        
        # Parse key-value pairs
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == "user-agent":
                current_agent = value
                if current_agent not in result["agents"]:
                    result["agents"][current_agent] = {"allow": [], "disallow": []}
            
            elif key == "allow" and current_agent:
                result["agents"][current_agent]["allow"].append(value)
            
            elif key == "disallow" and current_agent:
                result["agents"][current_agent]["disallow"].append(value)
            
            elif key == "crawl-delay" and current_agent:
                try:
                    result["crawl_delay"] = float(value)
                except ValueError:
                    pass
            
            elif key == "sitemap":
                result["sitemaps"].append(value)
            
            elif key == "host":
                result["host"] = value
    
    return result


def get_sitemaps_from_robots(base_url: str) -> List[str]:
    """Get sitemap URLs from robots.txt."""
    robots = parse_robots_txt(base_url)
    return robots.get("sitemaps", [])


def is_url_allowed(url: str, user_agent: str = "*") -> bool:
    """Check if a URL is allowed by robots.txt rules."""
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"
        
        robots = parse_robots_txt(base_url)
        agents = robots.get("agents", {})
        
        # Check specific agent first, then wildcard
        for agent in [user_agent, "*"]:
            if agent in agents:
                rules = agents[agent]
                
                # Check disallow rules
                for disallow in rules.get("disallow", []):
                    if disallow == "/" and path == "/":
                        return False
                    if path.startswith(disallow):
                        # Check if there's a more specific allow rule
                        for allow in rules.get("allow", []):
                            if path.startswith(allow) and len(allow) > len(disallow):
                                return True
                        return False
        
        return True
        
    except Exception:
        return True  # Allow if we can't parse


# ---------------------------------------------------------------------------
# Sitemap.xml Parser
# ---------------------------------------------------------------------------

def parse_sitemap(sitemap_url: str, timeout: int = 30) -> Dict[str, Any]:
    """Parse a sitemap.xml file.
    
    Handles:
    - Standard sitemap.xml
    - Sitemap index files (sitemap_index.xml)
    - Gzipped sitemaps (.xml.gz)
    - RSS/Atom feeds as sitemaps
    
    Returns:
        {
            "urls": ["https://example.com/page1", ...],
            "sitemaps": ["https://example.com/sitemap2.xml"],  # For index files
            "total_urls": 100,
            "lastmod": {"url": "2024-01-01"},
            "changefreq": {"url": "daily"},
            "priority": {"url": "0.8"}
        }
    """
    try:
        resp = httpx.get(
            sitemap_url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        
        content = resp.text
        
        # Check if it's a sitemap index
        if "<sitemapindex" in content.lower():
            return _parse_sitemap_index(content, sitemap_url)
        
        # Regular sitemap
        return _parse_urlset(content)
        
    except Exception as exc:
        logger.debug(f"Failed to parse sitemap {sitemap_url}: {exc}")
        return {"urls": [], "sitemaps": [], "total_urls": 0}


def _parse_urlset(xml_content: str) -> Dict[str, Any]:
    """Parse a URL set sitemap."""
    result = {
        "urls": [],
        "sitemaps": [],
        "total_urls": 0,
        "lastmod": {},
        "changefreq": {},
        "priority": {},
    }
    
    try:
        # Strip namespaces to simplify parsing
        content = re.sub(r'xmlns="[^"]*"', '', xml_content)
        content = re.sub(r'<s:', '<', content)
        content = re.sub(r'</s:', '</', content)
        
        root = ET.fromstring(content)
        
        for url_elem in root.findall(".//url"):
            loc = url_elem.find("loc")
            
            if loc is not None and loc.text:
                url = loc.text.strip()
                result["urls"].append(url)
                
                # Get optional fields
                lastmod = url_elem.find("lastmod")
                if lastmod is not None and lastmod.text:
                    result["lastmod"][url] = lastmod.text
                
                changefreq = url_elem.find("changefreq")
                if changefreq is not None and changefreq.text:
                    result["changefreq"][url] = changefreq.text
                
                priority = url_elem.find("priority")
                if priority is not None and priority.text:
                    result["priority"][url] = priority.text
        
        result["total_urls"] = len(result["urls"])
        
    except ET.ParseError as exc:
        logger.debug(f"XML parse error: {exc}")
        result = _parse_sitemap_regex(xml_content)
    
    return result


def _parse_sitemap_index(xml_content: str, base_url: str) -> Dict[str, Any]:
    """Parse a sitemap index file."""
    result = {
        "urls": [],
        "sitemaps": [],
        "total_urls": 0,
        "lastmod": {},
        "changefreq": {},
        "priority": {},
    }
    
    try:
        root = ET.fromstring(xml_content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        for sitemap_elem in root.findall("s:sitemap", ns) or root.findall("sitemap"):
            loc = sitemap_elem.find("s:loc", ns) or sitemap_elem.find("loc")
            
            if loc is not None and loc.text:
                sitemap_url = loc.text.strip()
                result["sitemaps"].append(sitemap_url)
        
    except ET.ParseError:
        # Fallback to regex
        pattern = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE)
        for match in pattern.finditer(xml_content):
            url = match.group(1).strip()
            if "sitemap" in url.lower():
                result["sitemaps"].append(url)
    
    return result


def _parse_sitemap_regex(xml_content: str) -> Dict[str, Any]:
    """Fallback regex-based sitemap parser."""
    result = {
        "urls": [],
        "sitemaps": [],
        "total_urls": 0,
        "lastmod": {},
        "changefreq": {},
        "priority": {},
    }
    
    # Extract URLs
    url_pattern = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE)
    for match in url_pattern.finditer(xml_content):
        url = match.group(1).strip()
        if url.startswith("http"):
            result["urls"].append(url)
    
    result["total_urls"] = len(result["urls"])
    return result


def discover_sitemaps(base_url: str) -> List[str]:
    """Discover all sitemaps for a website.
    
    Checks:
    1. robots.txt
    2. Common sitemap locations
    """
    sitemaps = set()
    
    # Check robots.txt first
    robots_sitemaps = get_sitemaps_from_robots(base_url)
    sitemaps.update(robots_sitemaps)
    
    # Check common sitemap locations
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    common_locations = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps.xml",
        "/sitemap/sitemap.xml",
        "/wp-sitemap.xml",
    ]
    
    for location in common_locations:
        try:
            url = base + location
            resp = httpx.head(url, headers={"User-Agent": ua_rotator.get()}, timeout=10)
            if resp.status_code == 200:
                sitemaps.add(url)
        except Exception:
            continue
    
    return list(sitemaps)


def get_all_urls_from_sitemap(base_url: str, max_urls: int = 1000) -> List[str]:
    """Get all URLs from a website's sitemaps.
    
    Args:
        base_url: Website URL
        max_urls: Maximum number of URLs to return
    
    Returns:
        List of URLs found in sitemaps
    """
    all_urls = []
    
    # Discover sitemaps
    sitemaps = discover_sitemaps(base_url)
    
    for sitemap_url in sitemaps:
        sitemap_data = parse_sitemap(sitemap_url)
        
        # If it's a sitemap index, parse each sub-sitemap
        if sitemap_data.get("sitemaps"):
            for sub_sitemap in sitemap_data["sitemaps"]:
                sub_data = parse_sitemap(sub_sitemap)
                all_urls.extend(sub_data.get("urls", []))
                
                if len(all_urls) >= max_urls:
                    return all_urls[:max_urls]
        else:
            all_urls.extend(sitemap_data.get("urls", []))
        
        if len(all_urls) >= max_urls:
            break
    
    return all_urls[:max_urls]


# ---------------------------------------------------------------------------
# Website Structure Discovery
# ---------------------------------------------------------------------------

def discover_website_structure(base_url: str, max_depth: int = 2) -> Dict[str, Any]:
    """Discover website structure using sitemaps and robots.txt.
    
    Returns:
        {
            "base_url": "https://example.com",
            "sitemaps": ["https://example.com/sitemap.xml"],
            "total_urls": 150,
            "urls_by_section": {
                "/blog/": ["https://example.com/blog/post1", ...],
                "/products/": ["https://example.com/products/item1", ...],
                "/about/": ["https://example.com/about", ...]
            },
            "robots_rules": {...}
        }
    """
    result = {
        "base_url": base_url,
        "sitemaps": [],
        "total_urls": 0,
        "urls_by_section": {},
        "robots_rules": {},
    }
    
    # Get robots.txt rules
    robots = parse_robots_txt(base_url)
    result["robots_rules"] = robots
    
    # Get sitemaps
    sitemaps = discover_sitemaps(base_url)
    result["sitemaps"] = sitemaps
    
    # Get all URLs
    all_urls = get_all_urls_from_sitemap(base_url, max_urls=1000)
    result["total_urls"] = len(all_urls)
    
    # Group URLs by section
    for url in all_urls:
        parsed = urlparse(url)
        path = parsed.path or "/"
        
        # Get top-level section
        parts = [p for p in path.split("/") if p]
        section = "/" + parts[0] + "/" if parts else "/"
        
        if section not in result["urls_by_section"]:
            result["urls_by_section"][section] = []
        
        result["urls_by_section"][section].append(url)
    
    return result


# ---------------------------------------------------------------------------
# Sitemap Utilities
# ---------------------------------------------------------------------------

def filter_sitemap_urls(
    urls: List[str],
    pattern: str = None,
    section: str = None,
    exclude_pattern: str = None,
) -> List[str]:
    """Filter sitemap URLs by pattern or section."""
    filtered = urls
    
    if pattern:
        regex = re.compile(pattern, re.IGNORECASE)
        filtered = [url for url in filtered if regex.search(url)]
    
    if section:
        filtered = [url for url in filtered if url.startswith(section) or f"/{section}/" in url]
    
    if exclude_pattern:
        regex = re.compile(exclude_pattern, re.IGNORECASE)
        filtered = [url for url in filtered if not regex.search(url)]
    
    return filtered


def get_sitemap_stats(sitemap_url: str) -> Dict[str, Any]:
    """Get statistics about a sitemap."""
    data = parse_sitemap(sitemap_url)
    
    urls = data.get("urls", [])
    
    # Calculate stats
    domains = set()
    extensions = {}
    sections = {}
    
    for url in urls:
        parsed = urlparse(url)
        domains.add(parsed.netloc)
        
        # Count extensions
        path = parsed.path
        if "." in path:
            ext = path.rsplit(".", 1)[-1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
        
        # Count sections
        parts = [p for p in path.split("/") if p]
        section = parts[0] if parts else "root"
        sections[section] = sections.get(section, 0) + 1
    
    return {
        "total_urls": len(urls),
        "unique_domains": len(domains),
        "extensions": extensions,
        "sections": sections,
        "changefreq": data.get("changefreq", {}),
        "priority": data.get("priority", {}),
    }
