# -*- coding: utf-8 -*-
"""Agent Search Lite — MCP Server.

Provides Agent Search Lite as an MCP tool for use in Claude Code, Cursor, and other MCP-compatible tools.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    Prompt,
    PromptMessage,
    PromptArgument,
)

from agent_search.core import AgentSearchLite

logger = logging.getLogger(__name__)

# Initialize the search engine
search_engine = AgentSearchLite()

# Create the MCP server
app = Server("agent-search-lite")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search",
            description="Free web search using multiple backends (DDGS, GitHub, Jina, HackerNews, arXiv, Wikipedia)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                    "mode": {
                        "type": "string",
                        "description": "Search mode: general, code, academic, news, community",
                        "enum": ["general", "code", "academic", "news", "community"],
                        "default": "general",
                    },
                    "site": {
                        "type": "string",
                        "description": "Search specific site (e.g., github.com, wikipedia.org)",
                    },
                    "date_after": {
                        "type": "string",
                        "description": "Results after date (YYYY-MM-DD)",
                    },
                    "date_before": {
                        "type": "string",
                        "description": "Results before date (YYYY-MM-DD)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="extract",
            description="Extract content from URLs (converts to clean markdown)",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "URLs to extract content from",
                    },
                    "char_limit": {
                        "type": "integer",
                        "description": "Maximum characters to extract (default: 15000)",
                        "default": 15000,
                    },
                },
                "required": ["urls"],
            },
        ),
        Tool(
            name="doctor",
            description="Check backend status and availability",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 5)
            mode = arguments.get("mode", "general")
            site = arguments.get("site")
            date_after = arguments.get("date_after")
            date_before = arguments.get("date_before")
            
            result = search_engine.search(
                query,
                limit=limit,
                mode=mode,
                site=site,
                date_after=date_after,
                date_before=date_before,
            )
            
            if result["success"]:
                return [TextContent(type="text", text=json.dumps(result["data"], indent=2, ensure_ascii=False))]
            else:
                return [TextContent(type="text", text=f"Search failed: {result.get('error')}")]
        
        elif name == "extract":
            urls = arguments.get("urls", [])
            char_limit = arguments.get("char_limit", 15000)
            
            results = search_engine.extract(urls, char_limit=char_limit)
            return [TextContent(type="text", text=json.dumps(results, indent=2, ensure_ascii=False))]
        
        elif name == "doctor":
            report = search_engine.doctor_report()
            return [TextContent(type="text", text=report)]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as exc:
        logger.error("Tool call failed: %s", exc)
        return [TextContent(type="text", text=f"Error: {exc}")]


@app.list_prompts()
async def list_prompts() -> List[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="search_and_summarize",
            description="Search the web and summarize results",
            arguments=[
                PromptArgument(name="query", description="Search query", required=True),
                PromptArgument(name="limit", description="Number of results", required=False),
            ],
        ),
    ]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
