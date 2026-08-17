# -*- coding: utf-8 -*-
"""Agent Search Lite — SEO, GEO, AEO, and Structured Data Extractor.

Extracts all SEO metadata, structured data (JSON-LD, microdata, Open Graph),
Twitter Cards, and entity optimization data from any website.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Full SEO Extractor
# ---------------------------------------------------------------------------

def extract_seo_data(html: str, url: str = "") -> Dict[str, Any]:
    """Extract all SEO-related data from HTML.
    
    Includes:
    - Title tag
    - Meta description
    - Meta keywords
    - Canonical URL
    - Robots meta tag
    - Hreflang tags
    - Open Graph tags
    - Twitter Card tags
    - Schema.org JSON-LD
    - Microdata
    - Structured data
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return _extract_seo_regex(html, url)
    
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        seo_data = {
            "url": url,
            "title": _get_title(soup),
            "meta_description": _get_meta_description(soup),
            "meta_keywords": _get_meta_keywords(soup),
            "canonical": _get_canonical(soup),
            "robots": _get_robots(soup),
            "hreflang": _get_hreflang(soup),
            "viewport": _get_viewport(soup),
            "charset": _get_charset(soup),
            "author": _get_author(soup),
            "generator": _get_generator(soup),
            "theme_color": _get_theme_color(soup),
            "open_graph": _get_open_graph(soup),
            "twitter_card": _get_twitter_card(soup),
            "json_ld": _get_all_json_ld(soup),
            "microdata": _get_all_microdata(soup),
            "structured_data": _get_structured_data(soup),
            "headings": _get_headings(soup),
            "links": _get_links(soup, url),
            "images": _get_images(soup, url),
            "favicon": _get_favicon(soup, url),
            "amp_url": _get_amp_url(soup),
            "manifest": _get_manifest(soup),
            "sitemap": _get_sitemap(soup),
            "rss_feeds": _get_rss_feeds(soup),
            "geo_data": _get_geo_data(soup),
            "organization": _get_organization_data(soup),
            "breadcrumbs": _get_breadcrumbs(soup),
            "faq": _get_faq_data(soup),
            "howto": _get_howto_data(soup),
            "article": _get_article_data(soup),
            "product": _get_product_data(soup),
            "person": _get_person_data(soup),
            "event": _get_event_data(soup),
            "recipe": _get_recipe_data(soup),
            "video": _get_video_data(soup),
            "local_business": _get_local_business_data(soup),
        }
        
        return seo_data
        
    except Exception as exc:
        logger.debug("SEO extraction failed: %s", exc)
        return {}


def _get_title(soup) -> str:
    """Extract page title."""
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else ""


def _get_meta_description(soup) -> str:
    """Extract meta description."""
    meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    return meta.get("content", "") if meta else ""


def _get_meta_keywords(soup) -> str:
    """Extract meta keywords."""
    meta = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
    return meta.get("content", "") if meta else ""


def _get_canonical(soup) -> str:
    """Extract canonical URL."""
    link = soup.find("link", attrs={"rel": "canonical"})
    return link.get("href", "") if link else ""


def _get_robots(soup) -> str:
    """Extract robots meta tag."""
    meta = soup.find("meta", attrs={"name": re.compile(r"robots", re.I)})
    return meta.get("content", "") if meta else ""


def _get_hreflang(soup) -> Dict[str, str]:
    """Extract hreflang tags."""
    hreflangs = {}
    for link in soup.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        lang = link.get("hreflang", "")
        href = link.get("href", "")
        if lang and href:
            hreflangs[lang] = href
    return hreflangs


def _get_viewport(soup) -> str:
    """Extract viewport meta tag."""
    meta = soup.find("meta", attrs={"name": "viewport"})
    return meta.get("content", "") if meta else ""


def _get_charset(soup) -> str:
    """Extract charset."""
    meta = soup.find("meta", attrs={"charset": True})
    if meta:
        return meta.get("charset", "")
    meta = soup.find("meta", attrs={"http-equiv": re.compile(r"content-type", re.I)})
    return meta.get("content", "") if meta else ""


def _get_author(soup) -> str:
    """Extract author meta tag."""
    meta = soup.find("meta", attrs={"name": re.compile(r"author", re.I)})
    return meta.get("content", "") if meta else ""


def _get_generator(soup) -> str:
    """Extract generator meta tag."""
    meta = soup.find("meta", attrs={"name": re.compile(r"generator", re.I)})
    return meta.get("content", "") if meta else ""


def _get_theme_color(soup) -> str:
    """Extract theme-color meta tag."""
    meta = soup.find("meta", attrs={"name": "theme-color"})
    return meta.get("content", "") if meta else ""


def _get_open_graph(soup) -> Dict[str, str]:
    """Extract all Open Graph tags."""
    og_data = {}
    for tag in soup.find_all("meta", property=re.compile(r"^og:")):
        prop = tag.get("property", "").replace("og:", "")
        content = tag.get("content", "")
        if prop and content:
            og_data[prop] = content
    return og_data


def _get_twitter_card(soup) -> Dict[str, str]:
    """Extract all Twitter Card tags."""
    twitter_data = {}
    for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
        name = tag.get("name", "").replace("twitter:", "")
        content = tag.get("content", "")
        if name and content:
            twitter_data[name] = content
    return twitter_data


def _get_all_json_ld(soup) -> List[Dict[str, Any]]:
    """Extract all JSON-LD structured data."""
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def _get_all_microdata(soup) -> List[Dict[str, Any]]:
    """Extract all microdata."""
    results = []
    for item in soup.find_all(attrs={"itemscope": True}):
        data = _parse_microdata_item(item)
        if data:
            results.append(data)
    return results


def _parse_microdata_item(item) -> Dict[str, Any]:
    """Parse a single microdata item."""
    data = {}
    item_type = item.get("itemtype", "")
    if item_type:
        data["@type"] = item_type.split("/")[-1]
    
    for prop in item.find_all(attrs={"itemprop": True}):
        prop_name = prop.get("itemprop", "")
        if prop.name == "meta":
            data[prop_name] = prop.get("content", "")
        elif prop.name in ("a", "link"):
            data[prop_name] = prop.get("href", prop.get_text(strip=True))
        elif prop.name == "img":
            data[prop_name] = prop.get("src", "")
        else:
            data[prop_name] = prop.get_text(strip=True)
    
    return data


def _get_structured_data(soup) -> Dict[str, Any]:
    """Extract all structured data types."""
    return {
        "json_ld": _get_all_json_ld(soup),
        "microdata": _get_all_microdata(soup),
        "open_graph": _get_open_graph(soup),
        "twitter_card": _get_twitter_card(soup),
    }


def _get_headings(soup) -> Dict[str, List[str]]:
    """Extract all heading tags."""
    headings = {}
    for level in range(1, 7):
        tag = f"h{level}"
        headings[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
    return headings


def _get_links(soup, base_url: str = "") -> Dict[str, List[str]]:
    """Extract all links."""
    internal = []
    external = []
    
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("http"):
            if base_url and base_url in href:
                internal.append(href)
            else:
                external.append(href)
        elif href.startswith("/"):
            internal.append(href)
        elif href.startswith("#"):
            internal.append(href)
        elif href and not href.startswith("javascript:"):
            internal.append(href)
    
    return {"internal": internal[:50], "external": external[:50]}


def _get_images(soup, base_url: str = "") -> List[Dict[str, str]]:
    """Extract all images."""
    images = []
    for img in soup.find_all("img"):
        src = img.get("src", img.get("data-src", ""))
        if src:
            images.append({
                "src": src,
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            })
    return images[:20]


def _get_favicon(soup, base_url: str = "") -> str:
    """Extract favicon URL."""
    link = soup.find("link", attrs={"rel": re.compile(r"icon", re.I)})
    if link:
        return link.get("href", "")
    return ""


def _get_amp_url(soup) -> str:
    """Extract AMP URL."""
    link = soup.find("link", attrs={"rel": "amphtml"})
    return link.get("href", "") if link else ""


def _get_manifest(soup) -> str:
    """Extract web manifest URL."""
    link = soup.find("link", attrs={"rel": "manifest"})
    return link.get("href", "") if link else ""


def _get_sitemap(soup) -> str:
    """Extract sitemap URL from robots.txt or link."""
    # This would require a separate request to robots.txt
    return ""


def _get_rss_feeds(soup) -> List[str]:
    """Extract RSS/Atom feed URLs."""
    feeds = []
    for link in soup.find_all("link", attrs={"type": re.compile(r"application/(rss|atom)")}):
        href = link.get("href", "")
        if href:
            feeds.append(href)
    return feeds


def _get_geo_data(soup) -> Dict[str, str]:
    """Extract GEO (Google Entity Optimization) data."""
    geo = {}
    
    # Geo meta tags
    for meta in soup.find_all("meta", attrs={"name": re.compile(r"geo\.")}):
        name = meta.get("name", "").replace("geo.", "")
        content = meta.get("content", "")
        if name and content:
            geo[name] = content
    
    # Place name
    meta = soup.find("meta", attrs={"name": "place:location:latitude"})
    if meta:
        geo["latitude"] = meta.get("content", "")
    
    meta = soup.find("meta", attrs={"name": "place:location:longitude"})
    if meta:
        geo["longitude"] = meta.get("content", "")
    
    return geo


def _get_organization_data(soup) -> Dict[str, Any]:
    """Extract organization data from JSON-LD."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") in ["Organization", "Corporation", "LocalBusiness", "NGO", "EducationalOrganization"]:
            return item
    return {}


def _get_breadcrumbs(soup) -> List[Dict[str, str]]:
    """Extract breadcrumb data."""
    # Try JSON-LD first
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "BreadcrumbList":
            items = item.get("itemListElement", [])
            return [{"name": i.get("name", ""), "url": i.get("item", "")} for i in items]
    
    # Try microdata
    breadcrumbs = []
    for item in soup.find_all(attrs={"itemtype": re.compile(r"BreadcrumbList")}):
        for li in item.find_all(attrs={"itemprop": "itemListElement"}):
            name = li.find(attrs={"itemprop": "name"})
            url = li.find("a", href=True)
            if name:
                breadcrumbs.append({
                    "name": name.get_text(strip=True),
                    "url": url.get("href", "") if url else "",
                })
    
    return breadcrumbs


def _get_faq_data(soup) -> List[Dict[str, str]]:
    """Extract FAQ data for AEO."""
    faqs = []
    
    # Try JSON-LD
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "FAQPage":
            for q in item.get("mainEntity", []):
                faqs.append({
                    "question": q.get("name", ""),
                    "answer": q.get("acceptedAnswer", {}).get("text", ""),
                })
    
    # Try microdata
    for item in soup.find_all(attrs={"itemtype": re.compile(r"FAQPage")}):
        for q in item.find_all(attrs={"itemtype": re.compile(r"Question")}):
            name = q.find(attrs={"itemprop": "name"})
            answer = q.find(attrs={"itemtype": re.compile(r"Answer")})
            if name:
                faqs.append({
                    "question": name.get_text(strip=True),
                    "answer": answer.get_text(strip=True) if answer else "",
                })
    
    return faqs


def _get_howto_data(soup) -> Dict[str, Any]:
    """Extract HowTo data for AEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "HowTo":
            return {
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "steps": [s.get("text", "") for s in item.get("step", [])],
                "total_time": item.get("totalTime", ""),
                "yield": item.get("yield", ""),
            }
    return {}


def _get_article_data(soup) -> Dict[str, Any]:
    """Extract Article data for AEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") in ["Article", "NewsArticle", "BlogPosting", "ScholarlyArticle"]:
            return {
                "headline": item.get("headline", ""),
                "author": item.get("author", {}).get("name", "") if isinstance(item.get("author"), dict) else "",
                "date_published": item.get("datePublished", ""),
                "date_modified": item.get("dateModified", ""),
                "image": item.get("image", ""),
                "publisher": item.get("publisher", {}).get("name", "") if isinstance(item.get("publisher"), dict) else "",
            }
    return {}


def _get_product_data(soup) -> Dict[str, Any]:
    """Extract Product data for e-commerce SEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "Product":
            return {
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "brand": item.get("brand", {}).get("name", "") if isinstance(item.get("brand"), dict) else "",
                "price": item.get("offers", {}).get("price", "") if isinstance(item.get("offers"), dict) else "",
                "currency": item.get("offers", {}).get("priceCurrency", "") if isinstance(item.get("offers"), dict) else "",
                "availability": item.get("offers", {}).get("availability", "") if isinstance(item.get("offers"), dict) else "",
                "rating": item.get("aggregateRating", {}).get("ratingValue", "") if isinstance(item.get("aggregateRating"), dict) else "",
            }
    return {}


def _get_person_data(soup) -> Dict[str, Any]:
    """Extract Person data for GEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "Person":
            return {
                "name": item.get("name", ""),
                "job_title": item.get("jobTitle", ""),
                "url": item.get("url", ""),
                "image": item.get("image", ""),
                "same_as": item.get("sameAs", []),
            }
    return {}


def _get_event_data(soup) -> Dict[str, Any]:
    """Extract Event data."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "Event":
            return {
                "name": item.get("name", ""),
                "start_date": item.get("startDate", ""),
                "end_date": item.get("endDate", ""),
                "location": item.get("location", {}).get("name", "") if isinstance(item.get("location"), dict) else "",
                "description": item.get("description", ""),
            }
    return {}


def _get_recipe_data(soup) -> Dict[str, Any]:
    """Extract Recipe data for AEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "Recipe":
            return {
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "author": item.get("author", {}).get("name", "") if isinstance(item.get("author"), dict) else "",
                "prep_time": item.get("prepTime", ""),
                "cook_time": item.get("cookTime", ""),
                "total_time": item.get("totalTime", ""),
                "recipe_yield": item.get("recipeYield", ""),
                "recipe_ingredients": item.get("recipeIngredient", []),
                "recipe_instructions": [s.get("text", "") for s in item.get("recipeInstructions", [])],
            }
    return {}


def _get_video_data(soup) -> Dict[str, Any]:
    """Extract Video data for AEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") == "VideoObject":
            return {
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "thumbnail": item.get("thumbnailUrl", ""),
                "upload_date": item.get("uploadDate", ""),
                "duration": item.get("duration", ""),
            }
    return {}


def _get_local_business_data(soup) -> Dict[str, Any]:
    """Extract LocalBusiness data for local SEO."""
    for item in _get_all_json_ld(soup):
        if item.get("@type") in ["LocalBusiness", "Restaurant", "Hotel", "Store"]:
            address = item.get("address", {})
            if isinstance(address, dict):
                address_str = f"{address.get('streetAddress', '')}, {address.get('addressLocality', '')}, {address.get('addressRegion', '')} {address.get('postalCode', '')}"
            else:
                address_str = address
            
            geo = item.get("geo", {})
            if isinstance(geo, dict):
                lat = geo.get("latitude", "")
                lon = geo.get("longitude", "")
            else:
                lat = lon = ""
            
            return {
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "address": address_str,
                "telephone": item.get("telephone", ""),
                "price_range": item.get("priceRange", ""),
                "latitude": lat,
                "longitude": lon,
                "opening_hours": item.get("openingHours", []),
            }
    return {}


def _extract_seo_regex(html: str, url: str = "") -> Dict[str, Any]:
    """Fallback SEO extraction using regex (no BeautifulSoup)."""
    seo_data = {"url": url}
    
    # Title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    seo_data["title"] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""
    
    # Meta description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    seo_data["meta_description"] = desc_match.group(1) if desc_match else ""
    
    # Canonical
    canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    seo_data["canonical"] = canonical_match.group(1) if canonical_match else ""
    
    # Robots
    robots_match = re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    seo_data["robots"] = robots_match.group(1) if robots_match else ""
    
    # JSON-LD
    seo_data["json_ld"] = []
    for match in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            seo_data["json_ld"].append(data)
        except json.JSONDecodeError:
            continue
    
    return seo_data


# ---------------------------------------------------------------------------
# Quick Extract Functions
# ---------------------------------------------------------------------------

def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract all meta tags."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name", meta.get("property", ""))
            content = meta.get("content", "")
            if name and content:
                meta_tags[name] = content
        
        return meta_tags
    except ImportError:
        return {}


def extract_json_ld(html: str) -> List[Dict[str, Any]]:
    """Extract all JSON-LD structured data."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return _get_all_json_ld(soup)
    except ImportError:
        return []


def extract_open_graph(html: str) -> Dict[str, str]:
    """Extract Open Graph tags."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return _get_open_graph(soup)
    except ImportError:
        return {}


def extract_twitter_card(html: str) -> Dict[str, str]:
    """Extract Twitter Card tags."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return _get_twitter_card(soup)
    except ImportError:
        return {}


def extract_microdata(html: str) -> List[Dict[str, Any]]:
    """Extract microdata."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return _get_all_microdata(soup)
    except ImportError:
        return []


def extract_all_structured_data(html: str, url: str = "") -> Dict[str, Any]:
    """Extract all structured data from a webpage.
    
    This is the main function to call for comprehensive extraction.
    """
    return extract_seo_data(html, url)
