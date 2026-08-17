# Changelog

All notable changes to Agent Search Lite will be documented in this file.

## [2.2.0] - 2026-08-16

### Added
- **SSR Content Extraction**: smart_extract() with JSON-LD, microdata, Open Graph
- **Result Ranking**: rank_results() with quality, verification, and relevance scoring
- **Pollution Detection**: is_polluted() filters spam/low-quality results
- **Cross-Verification**: cross_verify() marks results verified by multiple sources
- **Token-Conscious Formatting**: format_token_conscious() minimizes token usage
- **CLI Enhancements**: --token-conscious, --max-tokens, --no-smart flags

### Changed
- Search results now include relevance_score and verification_score
- Extract uses smart extraction by default (SSR, JSON-LD, readability)
- Updated attribution to include searchpin and WebSearchFree inspirations

## [2.1.1] - 2026-08-16

### Added
- Custom exception classes (AgentSearchError, BackendError, etc.)
- Graceful degradation with user-friendly messages
- Per-backend error tracking
- Proper attribution to upstream projects

## [2.1.0] - 2026-08-16

### Added
- Query Expansion: generates 3-5 reformulations per query
- Strategy Modes: general, code, academic, news, community
- BeautifulSoup content extraction with readability scoring

## [2.0.0] - 2026-08-16

### Added
- 6 Free Backends: SearXNG, GitHub, Hacker News, Reddit, DDGS, Jina+DDG
- Parallel backend execution
- SQLite caching with TTL
- URL resolution (direct URLs, no redirects)

## [1.0.0] - 2026-08-16

### Added
- Initial release
