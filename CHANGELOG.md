# Changelog

## [2.3.0] - 2026-08-16

### Fixed
- **DDGS backend now works**: Added `ddgs` package as pure Python DDG fallback
- **Better snippet parsing**: Multi-line snippet extraction from Jina results
- **Site-specific search**: `site:` operator to narrow to GitHub, Wikipedia, etc.
- **Date filters**: `after:YYYY-MM-DD` and `before:YYYY-MM-DD` support
- **HN API fixed**: Switched from broken Firebase to Algolia API
- **Removed broken Reddit**: 403 issue, will be replaced later

### Added
- **SearXNG Docker script**: One-command setup for self-hosted meta-search
- **CLI flags**: `--site`, `--after`, `--before` for advanced queries
- **Doctor report**: Now shows query operators and version

### Changed
- Updated strategy modes to remove broken Reddit backend
- Improved error handling throughout

## [2.2.0] - 2026-08-16

### Added
- SSR Content Extraction: JSON-LD, microdata, Open Graph
- Result Ranking: relevance_score, verification_score
- Pollution Detection: automatic spam filtering
- Cross-Verification: mark results verified by multiple sources
- Token-Conscious Formatting: minimize LLM token usage

## [2.1.1] - 2026-08-16

### Added
- Custom exception classes
- Graceful degradation with user-friendly messages
- Proper attribution to upstream projects

## [2.1.0] - 2026-08-16

### Added
- Query Expansion: 3-5 reformulations per query
- Strategy Modes: general, code, academic, news, community
- BeautifulSoup content extraction

## [2.0.0] - 2026-08-16

### Added
- 6 Free Backends with parallel execution
- SQLite caching
- URL resolution

## [1.0.0] - 2026-08-16

- Initial release
