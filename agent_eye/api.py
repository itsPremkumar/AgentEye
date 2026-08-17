# -*- coding: utf-8 -*-
"""AgentEye — FastAPI REST API.

Exposes AgentEye as a web service for any HTTP client.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_eye.core import AgentSearchLite

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgentEye API",
    description="Complete internet data access for AI agents — zero API keys, zero cost",
    version="6.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search = AgentSearchLite()


# ===========================================================================
# Request/Response Models
# ===========================================================================

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    mode: str = "general"
    site: Optional[str] = None
    date_after: Optional[str] = None
    date_before: Optional[str] = None
    lang: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExtractRequest(BaseModel):
    urls: List[str]
    char_limit: int = 15000


class SEORequest(BaseModel):
    urls: List[str]


class ResearchRequest(BaseModel):
    question: str
    sources: int = 10
    depth: int = 2


# ===========================================================================
# Endpoints
# ===========================================================================

@app.get("/")
async def root():
    return {
        "name": "AgentEye",
        "version": "6.5.0",
        "description": "Complete internet data access for AI agents",
        "endpoints": [
            "/search",
            "/extract",
            "/extract-seo",
            "/research",
            "/detect-capabilities",
            "/classify-website",
            "/check-availability",
            "/monitor",
            "/search-archive",
            "/doctor",
        ],
    }


@app.get("/search")
async def search_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    mode: str = Query("general", description="Search mode"),
    site: Optional[str] = None,
):
    """Search the web."""
    result = search.search(q, limit=limit, mode=mode, site=site)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))


@app.post("/search")
async def search_post(request: SearchRequest):
    """Search the web (POST)."""
    result = search.search(
        request.query,
        limit=request.limit,
        mode=request.mode,
        site=request.site,
    )
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))


@app.post("/extract")
async def extract(request: ExtractRequest):
    """Extract content from URLs."""
    results = search.extract(request.urls, char_limit=request.char_limit)
    return {"success": True, "results": results}


@app.post("/extract-seo")
async def extract_seo(request: SEORequest):
    """Extract SEO metadata from URLs."""
    results = search.extract_seo(request.urls)
    return {"success": True, "results": results}


@app.post("/research")
async def research(request: ResearchRequest):
    """Conduct research on a topic."""
    result = search.research_topic(request.question, sources=request.sources, depth=request.depth)
    return {"success": True, "result": result}


@app.get("/detect-capabilities")
async def detect_capabilities(url: str = Query(..., description="Website URL")):
    """Detect what a website supports."""
    result = search.detect_capabilities(url)
    return {"success": True, "capabilities": result}


@app.get("/classify-website")
async def classify_website(url: str = Query(..., description="Website URL")):
    """Classify website type."""
    result = search.classify_website(url)
    return {"success": True, "type": result}


@app.get("/check-availability")
async def check_availability(url: str = Query(..., description="Website URL")):
    """Check if a website is available."""
    result = search.check_availability(url)
    return {"success": True, "result": result}


@app.get("/monitor")
async def monitor(url: str = Query(..., description="URL to monitor")):
    """Monitor a URL for changes."""
    result = search.monitor_changes(url)
    return {"success": True, "result": result}


@app.get("/search-archive")
async def search_archive(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search Common Crawl archive."""
    result = search.search_archive(q, limit=limit)
    return {"success": True, "result": result}


@app.get("/doctor")
async def doctor():
    """Check backend status."""
    return {"success": True, "backends": search.doctor()}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "6.5.0"}


# ===========================================================================
# Run
# ===========================================================================

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
