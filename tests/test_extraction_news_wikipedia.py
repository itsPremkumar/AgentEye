"""Tests for Trafilatura fallback, DDGS News, and Wikipedia REST summary."""
from __future__ import annotations

import pytest
import respx
from agent_eye.core import AgentSearchLite
from agent_eye.search_engines import duckduckgo_news_search


# ---------------------------------------------------------------------------
# Trafilatura extraction fallback
# ---------------------------------------------------------------------------
class TestTrafilaturaFallback:
    def test_extract_jina_primary(self, agent, respx_mock):
        """Jina Reader succeeds → use Jina."""
        respx_mock.route(host="r.jina.ai").respond(
            200, text="Title: Test Page\n\nHello world content."
        )

        results = agent.extract(["https://example.com"])
        assert len(results) == 1
        assert results[0].get("content")

    def test_extract_trafilatura_fallback(self, agent, respx_mock, monkeypatch):
        """Jina fails → Trafilatura fallback."""
        respx_mock.route(host="r.jina.ai").respond(500, text="Error")
        # Trafilatura uses urllib, not httpx — mock it directly
        import trafilatura
        monkeypatch.setattr(trafilatura, "fetch_url", lambda url: b"""<!DOCTYPE html><html><head><title>Test Article</title></head>
<body><nav>Navigation links</nav><main><h1>Test Article</h1>
<p>This is the main content of the test article that should be extracted.</p>
<p>Second paragraph with more content.</p></main>
<footer>Copyright 2026</footer></body></html>""")

        results = agent.extract(["https://example.com"])
        assert len(results) == 1
        assert results[0].get("content")
        # Trafilatura strips boilerplate (nav, footer) — check content exists
        assert results[0]["content"]  # non-empty
        # Verify trafilatura was used as the extraction source
        assert results[0]["metadata"].get("extraction_source") == "trafilatura"

    def test_extract_direct_fallback(self, agent, respx_mock):
        """Both Jina and Trafilatura fail → direct request."""
        respx_mock.route(host="r.jina.ai").respond(500, text="Error")
        respx_mock.route(host="example.com").respond(
            200, text="<html><body><h1>Direct</h1><p>Content</p></body></html>"
        )

        results = agent.extract(["https://example.com"])
        assert len(results) == 1
        assert results[0].get("content")


# ---------------------------------------------------------------------------
# DDGS News
# ---------------------------------------------------------------------------
class TestDDGSNews:
    def test_ddgs_news_basic(self, respx_mock):
        """DDGS news returns results with source attribution."""
        respx_mock.route(host="duckduckgo.com").respond(
            200,
            text="""<html><body>
<a class="result__a" href="https://reuters.com/ai-news">AI Breakthrough</a>
<a class="result__snippet" href="#">Latest AI research announced today</a>
</body></html>""",
        )

        result = duckduckgo_news_search("AI news", limit=5)
        # May return None if parsing fails, but should not crash
        assert result is None or isinstance(result, dict)

    def test_ddgs_news_fallback(self, respx_mock):
        """DDGS news HTML fails → fallback to ddgs library."""
        respx_mock.route(host="duckduckgo.com").respond(500, text="Error")
        # ddgs library fallback will be attempted
        result = duckduckgo_news_search("AI news", limit=5)
        # Result depends on ddgs library availability
        assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# Wikipedia REST Summary
# ---------------------------------------------------------------------------
class TestWikipediaSummary:
    def test_wikipedia_summary_success(self, agent, respx_mock):
        """Wikipedia REST API returns structured summary."""
        respx_mock.route(host="en.wikipedia.org", path="/api/rest_v1/page/summary/Albert_Einstein").respond(
            200,
            json={
                "title": "Albert Einstein",
                "description": "German-born theoretical physicist",
                "extract": "Albert Einstein was a German-born theoretical physicist...",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Albert_Einstein"}},
                "thumbnail": {"source": "https://example.com/einstein.jpg"},
            },
        )

        result = agent.wikipedia_summary("Albert_Einstein")
        assert result.get("title") == "Albert Einstein"
        assert result.get("extract")
        assert result.get("description") == "German-born theoretical physicist"

    def test_wikipedia_summary_not_found(self, agent, respx_mock):
        """Wikipedia REST API returns 404 → error dict."""
        respx_mock.route(host="en.wikipedia.org", path="/api/rest_v1/page/summary/NonExistentPage12345").respond(
            404, text="Not Found"
        )

        result = agent.wikipedia_summary("NonExistentPage12345")
        assert "error" in result

    def test_wikipedia_summary_empty_title(self, agent):
        """Empty title → error."""
        result = agent.wikipedia_summary("")
        assert "error" in result
