# -*- coding: utf-8 -*-
"""Agent Search Lite — Advanced content extraction.

SSR-aware extraction with structured data (JSON-LD, microdata),
readability scoring, and anti-detection fallback.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured Data Extraction
# ---------------------------------------------------------------------------

def extract_json_ld(html: str) -> List[Dict[str, Any]]:
    """Extract JSON-LD structured data from HTML."""
    results = []
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except json.JSONDecodeError:
            continue
    return results


def extract_microdata(html: str) -> List[Dict[str, Any]]:
    """Extract microdata (itemscope/itemprop) from HTML."""
    results = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        for item in soup.find_all(attrs={"itemscope": True}):
            data = {}
            for prop in item.find_all(attrs={"itemprop": True}):
                prop_name = prop.get("itemprop")
                if prop.name in ["meta"]:
                    data[prop_name] = prop.get("content", "")
                elif prop.name in ["a", "link"]:
                    data[prop_name] = prop.get("href", prop.get_text(strip=True))
                elif prop.name in ["img"]:
                    data[prop_name] = prop.get("src", "")
                else:
                    data[prop_name] = prop.get_text(strip=True)
            if data:
                results.append(data)
    except ImportError:
        pass
    return results


def extract_open_graph(html: str) -> Dict[str, str]:
    """Extract Open Graph metadata from HTML."""
    og = {}
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("meta"):
            prop = tag.get("property", "")
            if prop.startswith("og:"):
                og[prop[3:]] = tag.get("content", "")
    except ImportError:
        pass
    return og


# ---------------------------------------------------------------------------
# Readability Scoring
# ---------------------------------------------------------------------------

def score_readability(text: str) -> float:
    """Score text readability (0.0 to 1.0).
    
    Based on paragraph density vs link density.
    Higher score = more readable content.
    """
    if not text:
        return 0.0
    
    lines = text.split("\n")
    non_empty = [l for l in lines if l.strip()]
    
    if not non_empty:
        return 0.0
    
    # Paragraph blocks (2+ consecutive non-empty lines)
    paragraphs = 0
    consecutive = 0
    for line in non_empty:
        if len(line) > 40:  # Likely content line
            consecutive += 1
        else:
            if consecutive >= 2:
                paragraphs += 1
            consecutive = 0
    if consecutive >= 2:
        paragraphs += 1
    
    # Link density (approximated by URL patterns)
    urls = len(re.findall(r'https?://\S+', text))
    words = len(text.split())
    
    if words == 0:
        return 0.0
    
    link_density = urls / (words / 100)  # URLs per 100 words
    
    # Score: high paragraphs, low link density = good
    paragraph_score = min(paragraphs / 10, 1.0)
    link_penalty = min(link_density / 5, 1.0)
    
    return max(0.0, min(1.0, paragraph_score - link_penalty * 0.5))


# ---------------------------------------------------------------------------
# Smart Content Extraction
# ---------------------------------------------------------------------------

def smart_extract(html: str, url: str = "", max_chars: int = 10000) -> Dict[str, Any]:
    """Smart content extraction with structured data priority.
    
    Extracts in priority order:
    1. JSON-LD structured data
    2. Open Graph metadata
    3. Microdata
    4. Readable text (readability scored)
    """
    result = {
        "url": url,
        "title": "",
        "content": "",
        "structured_data": None,
        "metadata": {},
        "readability_score": 0.0,
        "extraction_method": "none",
    }
    
    try:
        from bs4 import BeautifulSoup, Comment
    except ImportError:
        # Fallback to regex
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        result["content"] = text[:max_chars]
        result["extraction_method"] = "basic-regex"
        return result
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text(strip=True)
        
        # Extract structured data first
        json_ld = extract_json_ld(html)
        if json_ld:
            result["structured_data"] = {"json_ld": json_ld}
            result["extraction_method"] = "json-ld"
            
            # Try to build content from JSON-LD
            for item in json_ld:
                if item.get("@type") in ["Article", "NewsArticle", "BlogPosting"]:
                    parts = []
                    if item.get("headline"):
                        parts.append(f"# {item['headline']}")
                    if item.get("description"):
                        parts.append(item["description"])
                    if item.get("articleBody"):
                        parts.append(item["articleBody"])
                    if parts:
                        result["content"] = "\n\n".join(parts)[:max_chars]
                        break
        
        # Open Graph metadata
        og = extract_open_graph(html)
        if og:
            result["metadata"]["open_graph"] = og
            if not result["title"] and og.get("title"):
                result["title"] = og["title"]
        
        # Microdata
        microdata = extract_microdata(html)
        if microdata:
            result["structured_data"] = result.get("structured_data") or {}
            result["structured_data"]["microdata"] = microdata
        
        # If no structured content, extract readable text
        if not result["content"]:
            # Remove noise
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                element.decompose()
            for comment in soup.findAll(text=lambda t: isinstance(t, Comment)):
                comment.extract()
            
            # Try article/main content first
            main_content = soup.find(["article", "main"]) or soup.find(
                attrs={"role": "main"}
            ) or soup.find(class_=re.compile(r"(content|article|post|entry)", re.I))
            
            if main_content:
                text = main_content.get_text(separator="\n")
                result["extraction_method"] = "semantic-content"
            else:
                text = soup.get_text(separator="\n")
                result["extraction_method"] = "full-text"
            
            # Clean up
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            result["readability_score"] = score_readability(text)
            result["content"] = text[:max_chars]
        
    except Exception as exc:
        logger.warning("Smart extraction failed for %s: %s", url, exc)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        result["content"] = text[:max_chars]
        result["extraction_method"] = "fallback-regex"
    
    return result
