# Changelog

All notable changes to Agent Search Lite will be documented in this file.

## [2.1.0] - 2026-08-16

### Added
- **Query Expansion**: Generates 3-5 reformulations per query for better coverage
- **Strategy Modes**: `general`, `code`, `academic`, `news`, `community`
- **BeautifulSoup Content Extraction**: Smart extraction with readability scoring
- **Comprehensive Error Handling**: Custom exceptions with proper error types
  - `AgentSearchError` - Base exception
  - `BackendError` - Backend-specific failures
  - `AllBackendsFailedError` - When all backends fail
  - `InvalidURLError` - Invalid URL input
  - `InvalidModeError` - Invalid strategy mode
  - `CacheError` - Cache operation failures
  - `NetworkError` - Network connection issues
  - `RateLimitError` - Rate limit exceeded
  - `TimeoutError` - Request timeout
  - `ConfigurationError` - Invalid configuration
- **Proper Attribution**: Credits to Panniantong/Agent Reach and brcrusoe72/agent-search
- **CLI Enhancements**: `--mode`, `--no-expand`, `modes` command, `doctor` report

### Changed
- Improved error messages are now user-friendly
- Backend errors are tracked and reported per-backend
- Mode-specific backend prioritization

### Fixed
- URL resolution for DuckDuckGo redirect links
- Graceful handling of missing BeautifulSoup dependency

## [2.0.0] - 2026-08-16

### Added
- 6 Free Backends: SearXNG, GitHub, Hacker News, Reddit, DDGS, Jina+DDG
- Parallel backend execution
- SQLite caching with TTL
- URL resolution (direct URLs, no redirects)
- Retry with exponential backoff
- Smart deduplication

## [1.0.0] - 2026-08-16

### Added
- Initial release
- English-only version of Agent Reach
- 7 core channels
- Plugin-ready for Hermes Agent

---

Credits:
- Based on [Agent Reach](https://github.com/Panniantong/agent-reach) by Panniantong (MIT)
- Query expansion inspired by [brcrusoe72/agent-search](https://github.com/brcrusoe72/agent-search) (MIT)
