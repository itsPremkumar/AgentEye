from agent_eye.core import AgentSearchLite
import time

search = AgentSearchLite()

print('='*70)
print('AGENT SEARCH LITE — COMPREHENSIVE FEATURE VERIFICATION')
print('='*70)
print()

# Test 1: Backend count
print('TEST 1: Backend Status')
print('-'*50)
backends = search.doctor()
working = sum(1 for v in backends.values() if v == 'ok')
total = len(backends)
print(f'Backends: {working}/{total} working')
print()

# Test 2: Search
print('TEST 2: General Search')
print('-'*50)
result = search.search('AI agents 2026', limit=3, mode='general', use_cache=False)
if result['success']:
    print(f'Search OK: {len(result["data"]["web"])} results from {len(result["data"]["sources"])} sources')
else:
    print(f'Search failed: {result.get("error")}')
print()

# Test 3: Extract
print('TEST 3: Content Extraction')
print('-'*50)
extract = search.extract(['https://example.com'])
if extract and extract[0].get('content'):
    print(f'Extract OK: {len(extract[0]["content"])} chars')
else:
    print('Extract failed')
print()

# Test 4: SEO extraction
print('TEST 4: SEO Extraction')
print('-'*50)
seo = search.extract_seo(['https://github.com'])
if seo and seo[0].get('title'):
    print(f'SEO OK: {seo[0]["title"][:50]}')
else:
    print('SEO failed')
print()

# Test 5: Robots.txt
print('TEST 5: Robots.txt')
print('-'*50)
robots = search.get_robots('https://github.com')
if robots.get('agents'):
    print(f'Robots OK: {list(robots["agents"].keys())}')
else:
    print('Robots failed')
print()

# Test 6: Sitemaps
print('TEST 6: Sitemap Discovery')
print('-'*50)
sitemaps = search.get_sitemaps('https://www.bbc.com')
if sitemaps:
    print(f'Sitemaps OK: {len(sitemaps)} found')
else:
    print('Sitemaps failed')
print()

# Test 7: Sitemap URLs
print('TEST 7: Sitemap URLs')
print('-'*50)
urls = search.get_sitemap_urls('https://www.bbc.com', max_urls=5)
if urls:
    print(f'URLs OK: {len(urls)} found')
else:
    print('URLs failed')
print()

# Test 8: Website structure
print('TEST 8: Website Structure')
print('-'*50)
structure = search.get_website_structure('https://www.bbc.com')
if structure.get('total_urls') is not None:
    print(f'Structure OK: {structure["total_urls"]} URLs')
else:
    print('Structure failed')
print()

# Test 9: Check URL
print('TEST 9: URL Permission Check')
print('-'*50)
allowed = search.check_url_allowed('https://github.com/explore')
print(f'URL check OK: {"Allowed" if allowed else "Blocked"}')
print()

# Test 10: Feeds
print('TEST 10: Feed Discovery')
print('-'*50)
feeds = search.get_feeds('https://www.bbc.com')
print(f'Feeds OK: {len(feeds)} found')
print()

# Test 11: Wayback Machine
print('TEST 11: Wayback Machine')
print('-'*50)
wayback = search.wayback_history('https://github.com', limit=3)
if wayback:
    print(f'Wayback OK: {len(wayback)} snapshots')
else:
    print('Wayback failed')
print()

# Test 12: Suggestions
print('TEST 12: Search Suggestions')
print('-'*50)
suggestions = search.suggestions('Python async')
if suggestions:
    print(f'Suggestions OK: {len(suggestions)} found')
else:
    print('Suggestions failed')
print()

# Test 13: History
print('TEST 13: Search History')
print('-'*50)
history = search.history()
if history:
    print(f'History OK: {len(history)} searches')
else:
    print('History failed')
print()

# Test 14: Analytics
print('TEST 14: Search Analytics')
print('-'*50)
analytics = search.analytics()
if analytics.get('total_searches') is not None:
    print(f'Analytics OK: {analytics["total_searches"]} searches')
else:
    print('Analytics failed')
print()

# Test 15: Bookmark
print('TEST 15: Bookmarking')
print('-'*50)
from agent_eye.bookmarks import add_bookmark, load_bookmarks
add_bookmark('https://github.com/test', 'Test Bookmark', 'A test bookmark', ['test', 'python'])
bookmarks = load_bookmarks()
if bookmarks:
    print(f'Bookmarks OK: {len(bookmarks)} saved')
else:
    print('Bookmarks failed')
print()

# Test 16: Export
print('TEST 16: Export')
print('-'*50)
result = search.search('test', limit=2, use_cache=False)
if result['success']:
    json_out = search.export(result['data']['web'], 'json')
    csv_out = search.export(result['data']['web'], 'csv')
    md_out = search.export(result['data']['web'], 'markdown', 'test')
    print(f'Export OK: JSON({len(json_out)}), CSV({len(csv_out)}), MD({len(md_out)})')
else:
    print('Export failed')
print()

# Test 17: Crawl
print('TEST 17: Website Crawl')
print('-'*50)
crawl = search.crawl('https://example.com', max_pages=3)
if crawl.get('total_urls') is not None:
    print(f'Crawl OK: {crawl["total_urls"]} URLs, {crawl["crawled"]} crawled')
else:
    print('Crawl failed')
print()

# Test 18: Feed parse
print('TEST 18: Feed Parse')
print('-'*50)
feed = search.parse_feed('https://news.ycombinator.com/rss')
if feed.get('items'):
    print(f'Feed OK: {len(feed["items"])} items')
else:
    print('Feed failed')
print()

# Test 19: Compare
print('TEST 19: Compare')
print('-'*50)
from agent_eye.templates import compare_results
comparison = compare_results(
    [{'url': 'https://a.com', 'title': 'A'}, {'url': 'https://b.com', 'title': 'B'}],
    [{'url': 'https://a.com', 'title': 'A'}, {'url': 'https://c.com', 'title': 'C'}]
)
if comparison.get('similarity') is not None:
    print(f'Compare OK: {comparison["similarity"]:.2f} similarity')
else:
    print('Compare failed')
print()

# Test 20: Content search
print('TEST 20: Content Search')
print('-'*50)
from agent_eye.templates import search_content
matches = search_content('This is a test about Python async programming. Python is great.', 'Python', 20)
if matches:
    print(f'Content search OK: {len(matches)} matches')
else:
    print('Content search failed')
print()

# Test 21: Templates
print('TEST 21: Templates')
print('-'*50)
from agent_eye.templates import get_template_names, apply_template
templates = get_template_names()
template = apply_template('code_search', topic='async HTTP', lang='python')
if templates and template:
    print(f'Templates OK: {len(templates)} templates, applied: {template["query"][:30]}')
else:
    print('Templates failed')
print()

# Test 22: Batch process
print('TEST 22: Batch Process')
print('-'*50)
from agent_eye.batch_collector import batch_process_urls
batch = batch_process_urls(['https://example.com'], extract_content=True, extract_seo=False, max_workers=1)
if batch:
    print(f'Batch OK: {len(batch)} URLs processed')
else:
    print('Batch failed')
print()

print('='*70)
print('ALL TESTS COMPLETED')
print('='*70)
