# -*- coding: utf-8 -*-
"""AgentEye — Expanded MCP Server.

20+ tools following the Firecrawl/SearXNG MCP pattern.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agent_eye.core import AgentSearchLite
from agent_eye.extractors import smart_extract

logger = logging.getLogger(__name__)

search_engine = AgentSearchLite()
app = Server("agent-search-lite")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools (20+)."""
    return [
        # Search tools
        Tool(name="search", description="Free web search using 45+ backends", inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default: 5)", "default": 5},
                "mode": {"type": "string", "description": "Search mode", "enum": ["general", "code", "academic", "news", "community"]},
                "site": {"type": "string", "description": "Search specific site"},
            },
            "required": ["query"],
        }),
        Tool(name="google_search", description="Search Google directly (no API key)", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="bing_search", description="Search Bing directly", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="brave_search", description="Search Brave directly", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="duckduckgo_search", description="Search DuckDuckGo (enhanced)", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="github_search", description="Search GitHub repositories", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="stackoverflow_search", description="Search Stack Overflow", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="arxiv_search", description="Search arXiv academic papers", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="pubmed_search", description="Search PubMed medical papers", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="wikipedia_search", description="Search Wikipedia", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        # Extract tools
        Tool(name="extract", description="Extract content from URLs (markdown)", inputSchema={
            "type": "object",
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}},
                "char_limit": {"type": "integer", "default": 15000},
            },
            "required": ["urls"],
        }),
        Tool(name="extract_structured", description="Extract structured data (JSON-LD, microdata)", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        # Crawl tools
        Tool(name="crawl", description="Crawl a website for pages", inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_pages": {"type": "integer", "default": 10},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["url"],
        }),
        # Map/discover
        Tool(name="map_urls", description="Map all URLs on a website", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}, "limit": {"type": "integer", "default": 50}},
            "required": ["url"],
        }),
        # Knowledge
        Tool(name="weather", description="Get weather for a city (no API key)", inputSchema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        }),
        Tool(name="location_search", description="Search locations via OpenStreetMap", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="patent_search", description="Search US patents", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="book_search", description="Search books via OpenLibrary", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="anime_search", description="Search anime/manga", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="job_search", description="Search jobs", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "country": {"type": "string", "default": "us"}},
            "required": ["query"],
        }),
        Tool(name="search_archive", description="Search Common Crawl historical archive", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="detect_capabilities", description="Detect what a website supports", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="classify_website", description="Classify website type", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="check_availability", description="Check if a website is up", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="monitor", description="Monitor a URL for changes", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="research", description="Multi-step research with citations", inputSchema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "sources": {"type": "integer", "default": 10},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["question"],
        }),
        Tool(name="verify_source", description="Verify a source's reliability", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="extract_document", description="Extract PDF/DOCX/PPTX/XLSX content", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="extract_video", description="Extract video metadata via yt-dlp", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="extract_image", description="Extract image metadata and OCR text", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }),
        Tool(name="wayback_history", description="Get Wayback Machine history", inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["url"],
        }),
        Tool(name="nasa_apod", description="Get NASA Astronomy Picture of the Day", inputSchema={
            "type": "object", "properties": {},
        }),
        Tool(name="datamuse_words", description="Find similar words, rhymes, synonyms", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="usgs_earthquakes", description="Get recent earthquakes", inputSchema={
            "type": "object", "properties": {"limit": {"type": "integer", "default": 5}},
        }),
        Tool(name="social_search", description="Search social media platforms", inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "platform": {"type": "string", "enum": ["bluesky", "mastodon", "linkedin", "instagram", "tiktok", "x"]},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query", "platform"],
        }),
        Tool(name="cached_search", description="Search cached/indexed pages", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["query"],
        }),
        Tool(name="cache_stats", description="Get cache statistics", inputSchema={
            "type": "object", "properties": {},
        }),
        Tool(name="index_stats", description="Get search index statistics", inputSchema={
            "type": "object", "properties": {},
        }),
        Tool(name="clear_cache", description="Clear all cache levels", inputSchema={
            "type": "object", "properties": {},
        }),
        Tool(name="clear_index", description="Clear the search index", inputSchema={
            "type": "object", "properties": {},
        }),
        # Utility
        Tool(name="doctor", description="Check backend status", inputSchema={"type": "object", "properties": {}}),
        Tool(name="suggest", description="Get search suggestions", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}},
            "required": ["query"],
        }),
        Tool(name="compare", description="Compare two search queries", inputSchema={
            "type": "object",
            "properties": {
                "query1": {"type": "string"},
                "query2": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query1", "query2"],
        }),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search":
            result = search_engine.search(
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 5),
                mode=arguments.get("mode", "general"),
                site=arguments.get("site"),
            )
            if result["success"]:
                return [TextContent(type="text", text=json.dumps(result["data"], indent=2, ensure_ascii=False))]
            else:
                return [TextContent(type="text", text=f"Search failed: {result.get('error')}")]

        elif name == "google_search":
            from agent_eye.search_engines import google_search
            result = google_search(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "bing_search":
            from agent_eye.search_engines import bing_search
            result = bing_search(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "brave_search":
            from agent_eye.search_engines import brave_search
            result = brave_search(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "duckduckgo_search":
            from agent_eye.search_engines import duckduckgo_search
            result = duckduckgo_search(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "github_search":
            from agent_eye.core import _github_search
            result = _github_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "stackoverflow_search":
            from agent_eye.social import stackoverflow_search
            result = stackoverflow_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "arxiv_search":
            from agent_eye.academic import arxiv_search
            result = arxiv_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "pubmed_search":
            from agent_eye.academic_backends import pubmed_search
            result = pubmed_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "wikipedia_search":
            from agent_eye.academic import wikipedia_search
            result = wikipedia_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "extract":
            results = search_engine.extract(arguments["urls"], arguments.get("char_limit", 15000))
            return [TextContent(type="text", text=json.dumps(results, indent=2, ensure_ascii=False))]

        elif name == "extract_structured":
            from agent_eye.extractors import extract_json_ld, extract_microdata, extract_open_graph
            result = search_engine.extract([arguments["url"]])
            if result and result[0].get("content"):
                html = result[0].get("raw_content", "")
                structured = {
                    "json_ld": extract_json_ld(html),
                    "microdata": extract_microdata(html),
                    "open_graph": extract_open_graph(html),
                }
                return [TextContent(type="text", text=json.dumps(structured, indent=2, ensure_ascii=False))]
            return [TextContent(type="text", text="Could not extract")]

        elif name == "weather":
            from agent_eye.commerce_gov import weather_search
            result = weather_search(arguments["city"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "location_search":
            from agent_eye.knowledge_backends import osm_search
            result = osm_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "patent_search":
            from agent_eye.commerce_gov import patents_search
            result = patents_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "book_search":
            from agent_eye.media_backends import openlibrary_search
            result = openlibrary_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "anime_search":
            from agent_eye.media_backends import anilist_search
            result = anilist_search(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "job_search":
            from agent_eye.commerce_gov import jobs_search
            result = jobs_search(arguments["query"], arguments.get("country", "us"))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        # New tools
        elif name == "search_archive":
            result = search_engine.search_archive(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "detect_capabilities":
            result = search_engine.detect_capabilities(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "classify_website":
            result = search_engine.classify_website(arguments["url"])
            return [TextContent(type="text", text=f"Website type: {result}")]

        elif name == "check_availability":
            result = search_engine.check_availability(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "monitor":
            result = search_engine.monitor_changes(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "research":
            result = search_engine.research_topic(arguments["question"], arguments.get("sources", 10), arguments.get("depth", 2))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "verify_source":
            result = search_engine.verify_source(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "extract_document":
            result = search_engine.extract_document(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "Failed")]

        elif name == "extract_video":
            result = search_engine.extract_video(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "Failed")]

        elif name == "extract_image":
            result = search_engine.extract_image(arguments["url"])
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "Failed")]

        elif name == "wayback_history":
            result = search_engine.wayback_history(arguments["url"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2) if result else "No results")]

        elif name == "nasa_apod":
            from agent_eye.extra_apis import nasa_apod
            result = nasa_apod()
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "datamuse_words":
            from agent_eye.extra_apis import datamuse_words
            result = datamuse_words(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "usgs_earthquakes":
            from agent_eye.extra_apis import usgs_earthquakes
            result = usgs_earthquakes(limit=arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "social_search":
            from agent_eye.social_tiers import bluesky_search, mastodon_search, linkedin_public_search, instagram_public_search, tiktok_public_search, x_public_search
            platform = arguments.get("platform", "bluesky")
            query = arguments["query"]
            limit = arguments.get("limit", 5)
            search_fns = {
                "bluesky": bluesky_search,
                "mastodon": mastodon_search,
                "linkedin": linkedin_public_search,
                "instagram": instagram_public_search,
                "tiktok": tiktok_public_search,
                "x": x_public_search,
            }
            fn = search_fns.get(platform, bluesky_search)
            result = fn(query, limit)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "cached_search":
            result = search_engine.search_cached(arguments["query"], arguments.get("limit", 10))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False) if result else "No results")]

        elif name == "cache_stats":
            result = search_engine.get_cache_stats()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "index_stats":
            result = search_engine.get_index_stats()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "clear_cache":
            search_engine.clear_cache()
            return [TextContent(type="text", text="Cache cleared")]

        elif name == "clear_index":
            search_engine.clear_index()
            return [TextContent(type="text", text="Index cleared")]

        elif name == "doctor":
            return [TextContent(type="text", text=search_engine.doctor_report())]

        elif name == "suggest":
            suggestions = search_engine.suggestions(arguments["query"], arguments.get("limit", 5))
            return [TextContent(type="text", text=json.dumps(suggestions, indent=2))]

        elif name == "compare":
            r1 = search_engine.search(arguments["query1"], arguments.get("limit", 5))
            r2 = search_engine.search(arguments["query2"], arguments.get("limit", 5))
            from agent_eye.templates import compare_results
            comparison = compare_results(
                r1.get("data", {}).get("web", []),
                r2.get("data", {}).get("web", []),
            )
            return [TextContent(type="text", text=json.dumps(comparison, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as exc:
        logger.error("Tool call failed: %s", exc)
        return [TextContent(type="text", text=f"Error: {exc}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
