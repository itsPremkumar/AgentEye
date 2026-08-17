# -*- coding: utf-8 -*-
"""Agent Search Lite — Academic Backends.

PubMed, Semantic Scholar, CrossRef, OpenAlex.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
_CROSSREF_API = "https://api.crossref.org/works"
_OPENALEX_API = "https://api.openalex.org"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.0; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# PubMed Backend
# ---------------------------------------------------------------------------

def pubmed_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search PubMed for medical/biology research papers.
    
    Uses NCBI E-utilities API (free, no key required).
    """
    try:
        # First, search for IDs
        search_resp = httpx.get(
            f"{_PUBMED_API}/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return None
        
        # Then, fetch details
        fetch_resp = httpx.get(
            f"{_PUBMED_API}/efetch.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "xml",
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        fetch_resp.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(fetch_resp.text)
        results = []
        
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            article_data = medline.find("Article") if medline is not None else None
            
            if article_data is None:
                continue
            
            title_elem = article_data.find("ArticleTitle")
            abstract_elem = article_data.find("Abstract")
            
            title = title_elem.text if title_elem is not None else ""
            abstract = ""
            
            if abstract_elem is not None:
                abstract_texts = abstract_elem.findall("AbstractText")
                abstract = " ".join(t.text or "" for t in abstract_texts)
            
            # Get authors
            authors = []
            author_list = article_data.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None and fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")
            
            # Get journal
            journal_elem = article_data.find("Journal/JournalIssue/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Get year
            year_elem = article_data.find("Journal/JournalIssue/PubDate/Year")
            year = year_elem.text if year_elem is not None else ""
            
            # Get PMID
            pmid = medline.find("PMID")
            pmid_text = pmid.text if pmid is not None else ""
            
            results.append({
                "title": title,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                "description": abstract[:500] if abstract else "",
                "authors": ", ".join(authors[:3]),
                "journal": journal,
                "year": year,
                "source": "pubmed",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("PubMed search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# Semantic Scholar Backend
# ---------------------------------------------------------------------------

def semantic_scholar_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Semantic Scholar for academic papers.
    
    Free API, no key required (rate limited).
    """
    try:
        resp = httpx.get(
            f"{_SEMANTIC_SCHOLAR_API}/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "title,abstract,authors,year,citationCount,url",
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        papers = data.get("data", [])
        if not papers:
            return None
        
        results = []
        for i, paper in enumerate(papers[:limit]):
            authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
            
            results.append({
                "title": paper.get("title", ""),
                "url": paper.get("url", ""),
                "description": (paper.get("abstract", "") or "")[:500],
                "authors": ", ".join(authors),
                "year": paper.get("year", ""),
                "citations": paper.get("citationCount", 0),
                "source": "semantic_scholar",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Semantic Scholar search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# CrossRef Backend
# ---------------------------------------------------------------------------

def crossref_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search CrossRef for academic publications.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            _CROSSREF_API,
            params={
                "query": query,
                "rows": limit,
                "sort": "relevance",
                "order": "desc",
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get("message", {}).get("items", [])
        if not items:
            return None
        
        results = []
        for i, item in enumerate(items[:limit]):
            title = item.get("title", [""])[0] if item.get("title") else ""
            authors = [f"{a.get('given', '')} {a.get('family', '')}" for a in item.get("author", [])[:3]]
            
            results.append({
                "title": title,
                "url": item.get("URL", ""),
                "description": item.get("abstract", "")[:500] if item.get("abstract") else "",
                "authors": ", ".join(authors),
                "year": item.get("published-print", {}).get("date-parts", [[0]])[0][0] if item.get("published-print") else "",
                "type": item.get("type", ""),
                "source": "crossref",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("CrossRef search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# OpenAlex Backend
# ---------------------------------------------------------------------------

def openalex_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search OpenAlex for academic works.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_OPENALEX_API}/works",
            params={
                "search": query,
                "per-page": limit,
                "sort": "relevance_score:desc",
            },
            headers={"User-Agent": _UA},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        works = data.get("results", [])
        if not works:
            return None
        
        results = []
        for i, work in enumerate(works[:limit]):
            title = work.get("title", "")
            abstract = work.get("abstract_inverted_index", {})
            
            # Reconstruct abstract from inverted index
            if abstract:
                words = []
                for word, positions in abstract.items():
                    words.extend([word] * len(positions))
                abstract_text = " ".join(words[:100])
            else:
                abstract_text = ""
            
            authors = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])[:3]]
            
            results.append({
                "title": title,
                "url": work.get("doi", "") or work.get("id", ""),
                "description": abstract_text[:500],
                "authors": ", ".join(authors),
                "year": work.get("publication_year", ""),
                "cited_by": work.get("cited_by_count", 0),
                "source": "openalex",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("OpenAlex search failed: %s", exc)
    
    return None
