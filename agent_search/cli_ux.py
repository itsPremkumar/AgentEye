# -*- coding: utf-8 -*-
"""Agent Search Lite — CLI UX utilities.

Colors, progress bars, and formatted output.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Source-specific colors
    SOURCE_COLORS = {
        "github": "\033[95m",      # Magenta
        "hackernews": "\033[93m",  # Yellow
        "stackoverflow": "\033[96m", # Cyan
        "arxiv": "\033[94m",       # Blue
        "wikipedia": "\033[92m",   # Green
        "ddgs": "\033[97m",        # White
        "jina-ddg": "\033[97m",    # White
        "lemmy": "\033[91m",       # Red
        "mdn": "\033[94m",         # Blue
        "devto": "\033[95m",       # Magenta
        "searxng": "\033[96m",     # Cyan
    }


def supports_color() -> bool:
    """Check if terminal supports color."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Apply color to text if supported."""
    if not supports_color():
        return text
    return f"{color}{text}{Colors.RESET}"


def source_badge(source: str) -> str:
    """Get colored source badge."""
    color = Colors.SOURCE_COLORS.get(source, Colors.WHITE)
    return colorize(f"[{source}]", color)


def progress_bar(current: int, total: int, width: int = 40) -> str:
    """Generate a progress bar string."""
    if total == 0:
        return ""
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total}"


def spinner(message: str = "Searching") -> "Spinner":
    """Create a spinner context manager."""
    return Spinner(message)


class Spinner:
    """Simple terminal spinner."""
    
    def __init__(self, message: str = "Loading"):
        self.message = message
        self.running = False
    
    def __enter__(self):
        self.running = True
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.running = False
        # Clear the line
        sys.stdout.write("\r" + " " * (len(self.message) + 20) + "\r")
        sys.stdout.flush()
    
    def update(self, backends: List[str] = None):
        """Update spinner display."""
        if not self.running:
            return
        
        elapsed = time.time() - self.start_time
        msg = f"⏳ {self.message} ({elapsed:.1f}s)"
        if backends:
            msg += f" — {len(backends)} backends queried"
        
        sys.stdout.write(f"\r{msg}")
        sys.stdout.flush()


def print_results(results: List[Dict[str, Any]], query: str = "") -> None:
    """Print search results in a formatted way."""
    if not results:
        print(colorize("No results found.", Colors.YELLOW))
        return
    
    print()
    print(colorize(f"Results for: {query}", Colors.BOLD))
    print(colorize("=" * 60, Colors.DIM))
    
    for i, item in enumerate(results):
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        description = item.get("description", "")
        source = item.get("source", "?")
        relevance = item.get("relevance_score", 0)
        reliability = item.get("reliability_score", 0)
        
        # Print title
        print(f"{colorize(str(i+1), Colors.BOLD)}. {colorize(title, Colors.WHITE)}")
        
        # Print source badge
        print(f"   {source_badge(source)}", end="")
        
        # Print scores
        rel_color = Colors.GREEN if relevance > 0.7 else Colors.YELLOW if relevance > 0.4 else Colors.RED
        rel_text = colorize(f"rel: {relevance:.2f}", rel_color)
        print(f" {rel_text}", end="")
        
        if reliability > 0:
            rel_color = Colors.GREEN if reliability > 0.8 else Colors.YELLOW if reliability > 0.5 else Colors.RED
            rel_text = colorize(f"trust: {reliability:.2f}", rel_color)
            print(f" {rel_text}", end="")
        
        print()
        
        # Print URL
        if url:
            print(f"   {colorize(url, Colors.DIM)}")
        
        # Print description
        if description:
            print(f"   {colorize(description[:100], Colors.DIM)}")
        
        print()


def print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Print a simple table."""
    if not rows:
        return
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(colorize(header_line, Colors.BOLD))
    print(colorize("-" * len(header_line), Colors.DIM))
    
    # Print rows
    for row in rows:
        line = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(line)


def print_backends_status(backends: Dict[str, str]) -> None:
    """Print backend status in a formatted way."""
    print()
    print(colorize("Backend Status", Colors.BOLD))
    print(colorize("=" * 40, Colors.DIM))
    
    for name, status in backends.items():
        icon = "✅" if status == "ok" else "❌"
        color = Colors.GREEN if status == "ok" else Colors.RED
        print(f"  {icon} {name}: {colorize(status, color)}")
    print()


def print_suggestions(suggestions: List[str]) -> None:
    """Print search suggestions."""
    if not suggestions:
        return
    
    print(colorize("Suggestions:", Colors.BOLD))
    for s in suggestions:
        print(f"  {colorize('→', Colors.CYAN)} {s}")
    print()


def format_bytes(num_bytes: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"
