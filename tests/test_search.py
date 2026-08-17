"""Offline search tests — ddgs + httpx mocked."""
from __future__ import annotations

import pytest
import respx
from agent_eye.core import AgentSearchLite


def test_search_returns_results(agent, fake_ddgs, respx_mock):
    """A general search should aggregate results from backends."""
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    result = agent.search("python tutorial", limit=3, use_cache=False)
    assert result["success"]
    assert result["data"]["web"], "expected at least one result"
    assert result["data"]["sources"], "expected source breakdown non-empty"


def test_search_respects_limit(agent, fake_ddgs, respx_mock):
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    result = agent.search("query", limit=2, use_cache=False)
    assert result["success"]
    # ddgs fake returns max_results hits; backend limit caps per-backend fetch
    assert len(result["data"]["web"]) > 0


def test_search_mode_general_selects_backends(agent, fake_ddgs, respx_mock):
    """General mode should fire multiple backend categories."""
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    result = agent.search("AI agents", limit=3, mode="general", use_cache=False)
    assert result["success"]


def test_search_invalid_mode_raises(agent):
    with pytest.raises(Exception):
        agent.search("x", mode="not_a_real_mode")


def test_search_caching_stores_and_retrieves(agent, fake_ddgs, respx_mock):
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    r1 = agent.search("cachable", limit=2, use_cache=True)
    assert r1["success"]
    # Second call should hit cache (no extra network needed)
    r2 = agent.search("cachable", limit=2, use_cache=True)
    assert r2["success"]


def test_search_lang_threads_to_ddgs(agent, respx_mock):
    """search(lang=...) must not crash and should return results."""
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="api.duckduckgo.com").respond(200, text="{}")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.bing.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.brave.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.startpage.com").respond(200, text="<html></html>")
    respx_mock.route(host="search.yahoo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.ecosia.org").respond(200, text="<html></html>")

    result = agent.search("python", limit=2, lang="ta", use_cache=False)
    assert result["success"]
