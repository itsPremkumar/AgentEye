# Agent Search Lite — Completely Free Web Search for AI Agents

**Zero API keys. Zero cost. Multiple backends with parallel execution.**

Agent Search Lite provides **completely free** web search and content extraction for AI agents. No API keys, no signups, no billing — just works.

## Why Agent Search Lite?

Most web search backends require paid API keys (Firecrawl, Exa, Parallel, Tavily). Agent Search Lite fills the gap with **genuinely free** search from multiple sources:

| Backend | Cost | Type | Quality |
|---------|------|------|---------|
| **SearXNG** | Free (self-host) | Meta-search | ⭐⭐⭐⭐⭐ |
| **GitHub CLI** | Free | Code search | ⭐⭐⭐⭐⭐ |
| **Hacker News API** | Free | Tech news | ⭐⭐⭐⭐ |
| **Reddit JSON** | Free | Discussions | ⭐⭐⭐⭐ |
| **DDGS** | Free | DuckDuckGo | ⭐⭐⭐ |
| **Jina Reader** | Free | Web extraction | ⭐⭐⭐ |

## Features

- **Parallel execution**: All backends run simultaneously for diverse results
- **Smart deduplication**: No duplicate URLs in results
- **SQLite caching**: Repeat searches are instant
- **URL resolution**: Direct URLs, no redirect links
- **Retry with backoff**: Handles rate limits gracefully
- **Zero API keys**: Works out of the box
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

# Check backend status
print(search.doctor_report())
```

## CLI Usage

```bash
# Search
agent-search-lite search "Python 3.12 release" -n 5

# Extract
agent-search-lite extract https://example.com

# Check status
agent-search-lite doctor
```

## Optional: Add More Backends

### SearXNG (Self-Hosted Meta-Search)
```bash
docker run -d -p 8080:8080 searng/searxng
export SEARXNG_URL=http://localhost:8080
```

### DDGS Package (DuckDuckGo)
```bash
pip install agent-search-lite[ddgs]
```

## Architecture

```
Query
  │
  ├──→ SearXNG (self-hosted)
  ├──→ GitHub CLI
  ├──→ Hacker News API
  ├──→ Reddit JSON
  ├──→ DDGS (optional)
  └──→ Jina Reader + DDG HTML (fallback)
  │
  ▼
Deduplicated Results + SQLite Cache
```

## Backend Status

Run `agent-search-lite doctor` to see which backends are available:

```
Agent Search Lite — Backend Status
=============================================
  ✅ searxng: ok
  ✅ github: ok
  ✅ hackernews: ok
  ✅ reddit: ok
  ✅ ddgs: ok
  ✅ jina-ddg: ok
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

Based on [Agent Reach](https://github.com/Panniantong/agent-reach) by Panniantong (MIT licensed).
