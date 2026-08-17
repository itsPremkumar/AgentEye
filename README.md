# AgentLens — Complete Internet Data Access for AI Agents

**Zero API keys. Zero cost. 60+ free backends. Full internet data collection.**

AgentLens provides **completely free** internet data access for AI agents. No API keys, no signups, no billing — just works. Search, extract, crawl, and research the entire public web.

> **Backend reliability:** Most backends (Wikipedia, GitHub, arXiv, PubMed, Hacker News, OpenAlex, and the `ddgs`-powered sources) hit real, stable APIs and work out of the box. A few backends (Google, Bing, Brave, StartPage, Yahoo, Ecosia, DuckDuckGo-HTML) are *scrapers* — they parse search-engine HTML and break whenever that markup changes or a consent/JS page is served. When a scraper returns nothing, it **falls back automatically to `ddgs`** (tagged `"fallback_via": "ddgs"`), so you still get results. Scrapers are best-effort, not a guarantee.

## Why AgentLens?

Most web search backends require paid API keys (Firecrawl, Exa, Parallel, Tavily). AgentLens fills the gap with **genuinely free** access from 60+ sources across every category:

| Category | Backends | Count |
|----------|----------|-------|
| **Web Search** | Google, Bing, Brave, DuckDuckGo, StartPage, Mojeek, Qwant, SearXNG, DDGS, Jina | 10 |
| **Social Media** | Reddit, Twitter/X, YouTube, Mastodon, Telegram, Lemmy, Lobsters | 7 |
| **Academic** | arXiv, PubMed, Semantic Scholar, CrossRef, OpenAlex, Wikipedia | 6 |
| **Developer** | GitHub, GitLab, BitStackOverflow, npm, PyPI, Docker Hub, crates.io, Packagist, Go pkg | 10 |
| **Media** | TMDB, Last.fm, OpenLibrary, AniList, MAL, BoardGameAtlas, Unsplash, Pexels, Pixabay | 9 |
| **Knowledge** | Wikipedia, Wikidata, OpenStreetMap, GeoNames, DBpedia | 5 |
| **Government** | data.gov, World Bank, UN Data | 3 |
| **Finance** | Yahoo Finance | 1 |
| **Other** | Weather, Patents, Jobs, OpenCorporates, RSS, Wayback Machine, MDN, Dev.to, Hacker News | 9 |

## Features

- **Parallel execution**: All backends run simultaneously for diverse results
- **Smart deduplication**: No duplicate URLs in results
- **SQLite caching**: Repeat searches are instant
- **URL resolution**: Direct URLs, no redirect links
- **Retry with backoff**: Handles rate limits gracefully
- **Zero API keys**: Works out of the box
- **SEO/GEO/AEO extraction**: Full metadata from any website
- **Sitemap/Robots.txt parsing**: Discover website structure
- **Document intelligence**: PDF, DOCX, PPTX, XLSX extraction
- **Video metadata**: yt-dlp integration for 1000+ video platforms
- **Image OCR**: Extract text from images
- **Research mode**: Multi-step research with citations
- **Source verification**: Check reliability of any URL
- **Full website crawling**: Crawl any site via sitemaps
- **RSS/Atom parsing**: Monitor feeds and news
- **Wayback Machine**: Historical snapshots
- **Plugin-ready**: Embed as a Hermes Agent plugin

## Quick Start

```python
from agent_search.core import AgentSearchLite

search = AgentSearchLite()

# Search (runs all backends in parallel)
result = search.search("AI agent frameworks 2026", limit=5)
for item in result["data"]["web"]:
    print(f"{item['position']}. {item['title']} [{item['source']}]")

# Extract content from URLs
results = search.extract(["https://example.com"])

# Extract SEO metadata
seo = search.extract_seo(["https://github.com"])

# Crawl a website
crawl = search.crawl("https://example.com", max_pages=50)

# Research a topic
research = search.research_topic("best Python frameworks", sources=10, depth=2)

# Check backend status
print(search.doctor_report())
```

## CLI Usage

```bash
# Search
agent-search-lite search "Python 3.12 release" -n 5

# Extract content
agent-search-lite extract https://example.com

# Extract SEO metadata
agent-search-lite extract-seo https://github.com

# Crawl website
agent-search-lite crawl https://example.com --max-pages 50

# Get robots.txt
agent-search-lite robots https://github.com

# Discover sitemaps
agent-search-lite sitemaps https://bbc.com

# Get all URLs from sitemaps
agent-search-lite sitemap-urls https://bbc.com --max 100

# Parse RSS feed
agent-search-lite parse-feed https://news.ycombinator.com/rss

# Wayback Machine history
agent-search-lite wayback https://github.com --limit 10

# Research mode
agent-search-lite research "best Python frameworks" --sources 10 --depth 2

# Verify source
agent-search-lite verify-source https://github.com

# Check status
agent-search-lite doctor
```

## Optional: Add More Backends

### SearXNG (Self-Hosted Meta-Search)
```bash
docker run -d -p 8080:8080 searng/searxng
export SEARXNG_URL=http://localhost:8080
```

### yt-dlp (Video Intelligence)
```bash
pip install yt-dlp
```

### Tesseract (Image OCR)
```bash
# Windows
choco install tesseract

# macOS
brew install tesseract

# Linux
sudo apt install tesseract-ocr
```

## Architecture

```
Query
  │
  ├──→ Search Layer (60+ backends)
  │     ├── Web Search (Google, Bing, Brave, etc.)
  │     ├── Social Media (Reddit, Twitter, YouTube, etc.)
  │     ├── Academic (arXiv, PubMed, etc.)
  │     ├── Developer (GitHub, GitLab, etc.)
  │     └── Media (TMDB, Last.fm, etc.)
  │
  ├──→ Extraction Layer
  │     ├── HTML → Markdown
  │     ├── SEO Metadata (JSON-LD, OG, Twitter Cards)
  │     ├── Documents (PDF, DOCX, PPTX, XLSX)
  │     ├── Images (OCR, metadata)
  │     └── Video (metadata, subtitles)
  │
  ├──→ Crawling Layer
  │     ├── Sitemap.xml parsing
  │     ├── Robots.txt parsing
  │     ├── Recursive crawling
  │     └── RSS/Atom feeds
  │
  └──→ Intelligence Layer
        ├── Research mode
        ├── Source verification
        ├── Citation generation
        └── Change detection
```

## Backend Status

Run `agent-search-lite doctor` to see which backends are available:

```
AgentLens — Backend Status
=============================================
  ✅ google: ok
  ✅ bing: ok
  ✅ brave: ok
  ✅ duckduckgo: ok
  ✅ github: ok
  ✅ hackernews: ok
  ✅ arxiv: ok
  ✅ pubmed: ok
  ✅ wikipedia: ok
  ✅ stackoverflow: ok
  ✅ reddit: ok
  ✅ youtube: ok
  ✅ tmdb: ok
  ✅ lastfm: ok
  ✅ datagov: ok
  ✅ worldbank: ok
  ✅ yahoo_finance: ok
  ✅ weather: ok
  ✅ ... (60+ total)
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

Based on [Agent Reach](https://github.com/Panniantong/agent-reach) by Panniantong (MIT licensed).
Query expansion inspired by [brcrusoe72/agent-search](https://github.com/brcrusoe72/agent-search).
SSR extraction inspired by [telly6/searchpin](https://github.com/telly6/searchpin).
Ranking inspired by [drmikecrypto/WebSearchFree](https://github.com/drmikecrypto/WebSearchFree).
