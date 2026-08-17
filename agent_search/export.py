# -*- coding: utf-8 -*-
"""Agent Search Lite — Export utilities.

Export search results in JSON, CSV, and Markdown formats.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def export_json(results: List[Dict[str, Any]], indent: int = 2) -> str:
    """Export results as JSON string."""
    return json.dumps(results, indent=indent, ensure_ascii=False)


def export_csv(results: List[Dict[str, Any]]) -> str:
    """Export results as CSV string."""
    if not results:
        return ""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = ["position", "title", "url", "description", "source"]
    writer.writerow(headers)
    
    # Write rows
    for r in results:
        writer.writerow([
            r.get("position", ""),
            r.get("title", ""),
            r.get("url", ""),
            r.get("description", "")[:200],
            r.get("source", ""),
        ])
    
    return output.getvalue()


def export_markdown(results: List[Dict[str, Any]], query: str = "") -> str:
    """Export results as Markdown string."""
    lines = []
    
    if query:
        lines.append(f"# Search Results: {query}")
        lines.append("")
    
    for r in results:
        position = r.get("position", "")
        title = r.get("title", "")
        url = r.get("url", "")
        description = r.get("description", "")
        source = r.get("source", "")
        
        lines.append(f"## {position}. {title}")
        lines.append(f"**URL:** {url}")
        if source:
            lines.append(f"**Source:** {source}")
        if description:
            lines.append(f"**Description:** {description}")
        lines.append("")
    
    return "\n".join(lines)


def export(results: List[Dict[str, Any]], format: str = "json", query: str = "") -> str:
    """Export results in the specified format.
    
    Args:
        results: List of result dictionaries
        format: Export format (json, csv, markdown)
        query: Original search query (for markdown)
    
    Returns:
        Formatted string
    """
    format = format.lower()
    
    if format == "json":
        return export_json(results)
    elif format == "csv":
        return export_csv(results)
    elif format in ("markdown", "md"):
        return export_markdown(results, query)
    else:
        raise ValueError(f"Unsupported format: {format}. Use: json, csv, markdown")


def save_results(results: List[Dict[str, Any]], filepath: str, format: str = "json", query: str = "") -> None:
    """Save results to a file.
    
    Args:
        results: List of result dictionaries
        filepath: Output file path
        format: Export format
        query: Original search query
    """
    content = export(results, format, query)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info("Results saved to %s", filepath)
