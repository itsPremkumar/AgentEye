"""Offline extract / extract_seo / robots / sitemap tests."""
from __future__ import annotations

import pytest
from agent_eye.core import AgentSearchLite
from agent_eye.exceptions import InvalidURLError


def test_extract_basic(agent, respx_mock):
    respx_mock.route(host="example.com").respond(
        200, text="<html><head><title>Example</title></head>"
                   "<body><h1>Example Domain</h1><p>Hello world.</p></body></html>"
    )
    respx_mock.route(host="r.jina.ai").respond(
        200, text="Title: Example\n\nHello world."
    )

    results = agent.extract(["https://example.com"])
    assert len(results) == 1
    assert results[0].get("content")


def test_extract_invalid_url(agent):
    results = agent.extract(["ftp://bad"])
    assert "Invalid URL" in results[0]["error"]


def test_extract_seo(agent, respx_mock):
    respx_mock.route(host="github.com").respond(
        200, text="<html><head><title>GitHub: Let's build from here</title>"
                   '<meta property="og:title" content="GitHub"></head>'
                   "<body>Code hosting.</body></html>"
    )

    seo = agent.extract_seo(["https://github.com"])
    assert seo and seo[0].get("title")
    assert "GitHub" in seo[0]["title"]


def test_get_robots(agent, respx_mock):
    respx_mock.route(host="github.com", path="/robots.txt").respond(
        200, text="User-agent: *\nDisallow: /api/\nAllow: /\n"
    )

    robots = agent.get_robots("https://github.com")
    assert robots.get("agents", {}).get("*") is not None


def test_check_url_allowed(agent, respx_mock):
    respx_mock.route(host="example.com", path="/robots.txt").respond(
        200, text="User-agent: *\nDisallow: /private/\nAllow: /\n"
    )

    assert agent.check_url_allowed("https://example.com/public") is True
    assert agent.check_url_allowed("https://example.com/private/secret") is False


def test_get_sitemaps(agent, respx_mock):
    respx_mock.route(host="www.bbc.com", path="/robots.txt").respond(
        200, text="Sitemap: https://www.bbc.com/sitemap.xml\n"
    )
    # discover_sitemaps probes common locations via HEAD first
    respx_mock.route(host="www.bbc.com", path="/sitemap.xml").respond(200, text="")
    respx_mock.route(host="www.bbc.com", path="/sitemap_index.xml").respond(404)
    respx_mock.route(host="www.bbc.com", path="/sitemap-index.xml").respond(404)
    respx_mock.route(host="www.bbc.com", path="/sitemaps.xml").respond(404)
    respx_mock.route(host="www.bbc.com", path="/sitemap/sitemap.xml").respond(404)
    respx_mock.route(host="www.bbc.com", path="/wp-sitemap.xml").respond(404)

    sitemaps = agent.get_sitemaps("https://www.bbc.com")
    assert sitemaps, "expected at least one sitemap"


def test_get_sitemap_urls(agent, respx_mock):
    respx_mock.route(host="www.bbc.com", path="/robots.txt").respond(
        200, text="Sitemap: https://www.bbc.com/sitemap.xml\n"
    )
    respx_mock.route(host="www.bbc.com", path="/sitemap.xml").respond(
        200, text='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://www.bbc.com/1</loc></url>"
                "<url><loc>https://www.bbc.com/2</loc></url>"
                "</urlset>"
    )

    urls = agent.get_sitemap_urls("https://www.bbc.com", max_urls=5)
    assert len(urls) >= 2
