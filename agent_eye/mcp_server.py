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
