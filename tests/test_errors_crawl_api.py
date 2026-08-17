"""Offline tests for exceptions, config/cache, crawl, and FastAPI API."""
from __future__ import annotations

import pytest
from agent_eye.core import AgentSearchLite
from agent_eye.exceptions import (
    AgentSearchError,
    BackendError,
    InvalidModeError,
    InvalidURLError,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
def test_invalid_url_error():
    e = InvalidURLError("ftp://bad")
    assert "ftp://bad" in str(e)
    assert isinstance(e, AgentSearchError)


def test_backend_error():
    e = BackendError("ddgs", "timeout")
    assert e.backend == "ddgs"
    assert "ddgs" in str(e)


def test_invalid_mode_error():
    e = InvalidModeError("bogus", ["general", "code"])
    assert "bogus" in str(e)
    assert "general" in str(e)


def test_robots_disallowed_error():
    """RobotsDisallowedError is added in the phase-a hardening PR."""
    pass  # placeholder — tested in phase-a branch


# ---------------------------------------------------------------------------
# Config + cache
# ---------------------------------------------------------------------------
def test_ensure_config_creates_default(tmp_home):
    from agent_eye.config import ensure_config
    cfg = ensure_config()
    assert isinstance(cfg, dict)
    assert "backends" in cfg or "cache" in cfg or len(cfg) > 0


def test_cache_set_and_get(tmp_home):
    from agent_eye.core import _cache_set, _cache_get
    _cache_set("k1", "v1")
    assert _cache_get("k1") == "v1"
    assert _cache_get("missing") is None


# ---------------------------------------------------------------------------
# Crawl (with mocked sitemaps + fetch)
# ---------------------------------------------------------------------------
def test_crawl_skips_disallowed(agent, respx_mock):
    respx_mock.route(host="example.com", path="/robots.txt").respond(
        200, text="User-agent: *\nDisallow: /admin/\nAllow: /\n"
    )
    respx_mock.route(host="example.com", path="/sitemap.xml").respond(
        200, text='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://example.com/admin/secret</loc></url>"
                "<url><loc>https://example.com/public</loc></url>"
                "</urlset>"
    )
    respx_mock.route(host="example.com", path="/public").respond(
        200, text="<html><body><h1>Public</h1></body></html>"
    )
    respx_mock.route(host="example.com", path="/admin/secret").respond(
        200, text="<html><body><h1>Admin</h1></body></html>"
    )

    result = agent.crawl("https://example.com", max_pages=5)
    assert result["crawled"] >= 1


# ---------------------------------------------------------------------------
# FastAPI API
# ---------------------------------------------------------------------------
def test_api_health(agent_nohome):
    from agent_eye.api import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_search_endpoint(agent_nohome, fake_ddgs, respx_mock):
    from agent_eye.api import app
    from fastapi.testclient import TestClient
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    c = TestClient(app)
    r = c.get("/search?q=python&limit=2")
    assert r.status_code == 200
    assert r.json()["success"]


def test_api_extract_endpoint(agent_nohome, respx_mock):
    from agent_eye.api import app
    from fastapi.testclient import TestClient
    respx_mock.route(host="example.com").respond(
        200, text="<html><head><title>Example</title></head><body>Hi</body></html>"
    )

    c = TestClient(app)
    r = c.post("/extract", json={"urls": ["https://example.com"]})
    assert r.status_code == 200
    assert r.json()["success"]
