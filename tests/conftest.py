"""Shared fixtures for the offline test suite.

All network I/O is mocked so tests run without internet:

- ``respx`` intercepts every ``httpx`` request and returns canned responses.
- ``ddgs.DDGS`` is replaced with a fake client that yields canned hits.
- ``Path.home`` is redirected to a tmp dir so config/cache never touch the real
  filesystem.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import httpx
import pytest
import respx


# ---------------------------------------------------------------------------
# Home / config redirect
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch):
    """Point ``Path.home()`` at a tmp dir so ~/.agent-search is isolated."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    # core.py references Path.home() at import time inside functions; the
    # monkeypatch covers calls. Also patch the module-level CONFIG_DIR used by
    # config.py so ensure_config() writes into the tmp tree.
    monkeypatch.setattr("agent_eye.config.CONFIG_DIR", tmp_path / ".agent-search")
    monkeypatch.setattr("agent_eye.config.CONFIG_FILE",
                        tmp_path / ".agent-search" / "config.yaml")
    return tmp_path


# ---------------------------------------------------------------------------
# ddgs fake
# ---------------------------------------------------------------------------
class _FakeDDGS:
    """Minimal stand-in for ``ddgs.DDGS`` returning canned hits."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def text(self, query: str, max_results: int = 5, **kwargs) -> List[Dict[str, str]]:
        return [
            {"title": f"{query} — result {i}", "href": f"https://example.com/{i}",
             "body": f"Snippet for result {i} about {query}."}
            for i in range(max_results)
        ]


@pytest.fixture
def fake_ddgs(monkeypatch):
    """Replace ``ddgs.DDGS`` everywhere it's imported."""
    monkeypatch.setattr("agent_eye.core.DDGS", _FakeDDGS, raising=False)
    monkeypatch.setattr("agent_eye.search_engines.DDGS", _FakeDDGS, raising=False)
    # Also catch ``from ddgs import DDGS`` lazy imports by patching sys.modules.
    import sys
    fake_mod = mock.MagicMock()
    fake_mod.DDGS = _FakeDDGS
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)


# ---------------------------------------------------------------------------
# httpx mock
# ---------------------------------------------------------------------------
@pytest.fixture
def respx_mock():
    """A respx router active for the test."""
    with respx.mock(assert_all_called=False) as rp:
        yield rp


# ---------------------------------------------------------------------------
# Canned HTTP responses
# ---------------------------------------------------------------------------
def html_page(title: str = "Test Page", body: str = "Hello world") -> str:
    return f"""<!DOCTYPE html><html><head><title>{title}</title></head>
<body><h1>{title}</h1><p>{body}</p>
<a href="https://example.com/page2">link</a>
</body></html>"""


def robots_txt(allow: str = "/") -> str:
    return f"User-agent: *\nDisallow: /admin/\nDisallow: /private/\nAllow: {allow}\n"


def sitemap_xml(urls: List[str]) -> str:
    items = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'


# ---------------------------------------------------------------------------
# Fresh AgentSearchLite instance
# ---------------------------------------------------------------------------
@pytest.fixture
def agent(tmp_home, fake_ddgs):
    """Return a fresh ``AgentSearchLite`` using an isolated tmp home."""
    from agent_eye.core import AgentSearchLite
    return AgentSearchLite()


@pytest.fixture
def agent_nohome(fake_ddgs):
    """Return an agent without redirecting home (uses real cache, wiped after)."""
    from agent_eye.core import AgentSearchLite
    return AgentSearchLite()
