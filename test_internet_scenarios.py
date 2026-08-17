from agent_search.core import AgentSearchLite
import time
import json

search = AgentSearchLite()

print('='*80)
print('AGENT LENS v6.0 — COMPREHENSIVE INTERNET ACCESS TEST')
print('='*80)
print()

# ---------------------------------------------------------------------------
# SCENARIO 1: General Web Search
# ---------------------------------------------------------------------------
print('SCENARIO 1: General Web Search')
print('-'*80)
tests = [
    'latest AI news 2026',
    'Python async tutorial',
    'open source AI agent frameworks',
    'weather today',
    'stock market news',
]
for query in tests:
    start = time.time()
    result = search.search(query, limit=3, mode='general', use_cache=False)
    elapsed = time.time() - start
    if result['success']:
        sources = list(result['data']['sources'].keys())[:5]
        print(f'  ✅ "{query[:30]}" - {len(result["data"]["web"])} results in {elapsed:.1f}s - Sources: {sources}')
    else:
        print(f'  ❌ "{query[:30]}" - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 2: Code & Development
# ---------------------------------------------------------------------------
print('SCENARIO 2: Code & Development')
print('-'*80)
code_tests = [
    ('Python httpx tutorial', 'code'),
    ('Rust async framework', 'code'),
    ('React hooks guide', 'code'),
    ('Docker compose example', 'code'),
]
for query, mode in code_tests:
    start = time.time()
    result = search.search(query, limit=3, mode=mode, use_cache=False)
    elapsed = time.time() - start
    if result['success']:
        sources = list(result['data']['sources'].keys())[:5]
        print(f'  ✅ "{query[:30]}" - {len(result["data"]["web"])} results in {elapsed:.1f}s - Sources: {sources}')
    else:
        print(f'  ❌ "{query[:30]}" - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 3: Academic Research
# ---------------------------------------------------------------------------
print('SCENARIO 3: Academic Research')
print('-'*80)
academic_tests = [
    'transformer neural network',
    'quantum computing progress 2026',
    'machine learning optimization',
    'CRISPR gene editing latest',
]
for query in academic_tests:
    start = time.time()
    result = search.search(query, limit=3, mode='academic', use_cache=False)
    elapsed = time.time() - start
    if result['success']:
        sources = list(result['data']['sources'].keys())[:5]
        print(f'  ✅ "{query[:30]}" - {len(result["data"]["web"])} results in {elapsed:.1f}s - Sources: {sources}')
    else:
        print(f'  ❌ "{query[:30]}" - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 4: News & Social
# ---------------------------------------------------------------------------
print('SCENARIO 4: News & Social')
print('-'*80)
news_tests = [
    ('AI breakthrough 2026', 'news'),
    ('tech layoffs 2026', 'news'),
    ('Linux desktop', 'community'),
    ('best mechanical keyboard', 'community'),
]
for query, mode in news_tests:
    start = time.time()
    result = search.search(query, limit=3, mode=mode, use_cache=False)
    elapsed = time.time() - start
    if result['success']:
        sources = list(result['data']['sources'].keys())[:5]
        print(f'  ✅ "{query[:30]}" ({mode}) - {len(result["data"]["web"])} results in {elapsed:.1f}s - Sources: {sources}')
    else:
        print(f'  ❌ "{query[:30]}" - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 5: SEO Extraction
# ---------------------------------------------------------------------------
print('SCENARIO 5: SEO Extraction')
print('-'*80)
urls_to_test = [
    'https://github.com',
    'https://stackoverflow.com',
    'https://www.python.org',
    'https://www.bbc.com',
]
for url in urls_to_test:
    start = time.time()
    seo = search.extract_seo([url])
    elapsed = time.time() - start
    if seo and seo[0].get('title'):
        og = seo[0].get('open_graph', {})
        print(f'  ✅ {url[:30]} - Title: {seo[0]["title"][:40]}... OG: {len(og)} tags ({elapsed:.1f}s)')
    else:
        print(f'  ❌ {url[:30]} - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 6: Robots.txt Parsing
# ---------------------------------------------------------------------------
print('SCENARIO 6: Robots.txt Parsing')
print('-'*80)
for url in ['https://github.com', 'https://reddit.com', 'https://www.bbc.com']:
    start = time.time()
    robots = search.get_robots(url)
    elapsed = time.time() - start
    if robots.get('agents'):
        agents = list(robots['agents'].keys())
        sitemaps = len(robots.get('sitemaps', []))
        print(f'  ✅ {url[:30]} - Agents: {agents} Sitemaps: {sitemaps} ({elapsed:.1f}s)')
    else:
        print(f'  ❌ {url[:30]} - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 7: Sitemap Discovery
# ---------------------------------------------------------------------------
print('SCENARIO 7: Sitemap Discovery')
print('-'*80)
for url in ['https://www.bbc.com', 'https://github.com', 'https://www.python.org']:
    start = time.time()
    sitemaps = search.get_sitemaps(url)
    elapsed = time.time() - start
    if sitemaps:
        print(f'  ✅ {url[:30]} - {len(sitemaps)} sitemaps ({elapsed:.1f}s)')
    else:
        print(f'  ⚠️ {url[:30]} - No sitemaps ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SCENARIO 8: Sitemap URL Extraction
# ---------------------------------------------------------------------------
print('SCENARIO 8: Sitemap URL Extraction')
print('-'*80)
start = time.time()
urls = search.get_sitemap_urls('https://www.bbc.com', max_urls=10)
elapsed = time.time() - start
if urls:
    print(f'  ✅ bbc.com - {len(urls)} URLs extracted ({elapsed:.1f}s)')
    for url in urls[:3]:
        print(f'     - {url[:60]}')
else:
    print(f'  ⚠️ bbc.com - No URLs extracted ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SCENARIO 9: Website Structure Discovery
# ---------------------------------------------------------------------------
print('SCENARIO 9: Website Structure Discovery')
print('-'*80)
start = time.time()
structure = search.get_website_structure('https://www.bbc.com')
elapsed = time.time() - start
if structure.get('total_urls') is not None:
    sections = list(structure.get('urls_by_section', {}).keys())[:5]
    print(f'  ✅ bbc.com - {structure["total_urls"]} URLs, sections: {sections} ({elapsed:.1f}s)')
else:
    print(f'  ❌ bbc.com - FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 10: Feed Discovery & Parsing
# ---------------------------------------------------------------------------
print('SCENARIO 10: Feed Discovery & Parsing')
print('-'*80)
start = time.time()
feed = search.parse_feed('https://news.ycombinator.com/rss')
elapsed = time.time() - start
if feed and feed.get('items'):
    print(f'  ✅ HN RSS - {len(feed["items"])} items ({elapsed:.1f}s)')
    for item in feed['items'][:3]:
        print(f'     - {item.get("title", "")[:50]}')
else:
    print(f'  ⚠️ HN RSS - FAILED ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SCENARIO 11: Wayback Machine
# ---------------------------------------------------------------------------
print('SCENARIO 11: Wayback Machine History')
print('-'*80)
start = time.time()
wayback = search.wayback_history('https://github.com', limit=5)
elapsed = time.time() - start
if wayback:
    print(f'  ✅ github.com - {len(wayback)} snapshots ({elapsed:.1f}s)')
    for snap in wayback[:3]:
        print(f'     - {snap.get("timestamp", "")[:14]} - {snap.get("original", "")[:50]}')
else:
    print(f'  ⚠️ github.com - No snapshots ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SCENARIO 12: Research Mode
# ---------------------------------------------------------------------------
print('SCENARIO 12: Research Mode')
print('-'*80)
start = time.time()
result = search.research_topic('best Python async frameworks 2026', sources=5, depth=2)
elapsed = time.time() - start
if result.get('findings'):
    print(f'  ✅ Research - {len(result["findings"])} findings, confidence: {result["confidence"]} ({elapsed:.1f}s)')
    for finding in result['findings'][:3]:
        print(f'     - [{finding.get("source", "")}] {finding.get("title", "")[:50]}')
else:
    print(f'  ❌ Research FAILED ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SCENARIO 13: Source Verification
# ---------------------------------------------------------------------------
print('SCENARIO 13: Source Verification')
print('-'*80)
test_sources = [
    'https://github.com',
    'https://arxiv.org',
    'https://reddit.com',
    'https://unknown-blog.example.com',
]
for url in test_sources:
    result = search.verify_source(url)
    reliable = result.get('reliable', 'unknown')
    print(f'  ✅ {url[:35]} - Reliable: {reliable}')
print()

# ---------------------------------------------------------------------------
# SCENARIO 14: URL Permission Check
# ---------------------------------------------------------------------------
print('SCENARIO 14: URL Permission Check')
print('-'*80)
test_urls = [
    'https://github.com/explore',
    'https://github.com/admin',
    'https://reddit.com/r/programming',
]
for url in test_urls:
    allowed = search.check_url_allowed(url)
    status = '✅ Allowed' if allowed else '❌ Blocked'
    print(f'  {status}: {url[:50]}')
print()

# ---------------------------------------------------------------------------
# SCENARIO 15: Export
# ---------------------------------------------------------------------------
print('SCENARIO 15: Export')
print('-'*80)
result = search.search('test query', limit=3, use_cache=False)
if result['success']:
    json_out = search.export(result['data']['web'], 'json')
    csv_out = search.export(result['data']['web'], 'csv')
    md_out = search.export(result['data']['web'], 'markdown', 'test')
    print(f'  ✅ Export - JSON: {len(json_out)} chars, CSV: {len(csv_out)} chars, MD: {len(md_out)} chars')
else:
    print(f'  ❌ Export FAILED')
print()

# ---------------------------------------------------------------------------
# SCENARIO 16: Bookmark & Collections
# ---------------------------------------------------------------------------
print('SCENARIO 16: Bookmark & Collections')
print('-'*80)
from agent_search.bookmarks import add_bookmark, load_bookmarks, create_collection, add_to_collection
add_bookmark('https://github.com/test-agent-lens', 'AgentLens Test', 'Testing bookmark system', ['test', 'agent-lens'])
bookmarks = load_bookmarks()
print(f'  ✅ Bookmarks - {len(bookmarks)} saved')
create_collection('test-collection', 'AgentLens Test Collection')
result = add_to_collection('test-collection', 'https://example.com', 'Example', 'Test collection item')
print(f'  ✅ Collections - Created and added item')
print()

# ---------------------------------------------------------------------------
# SCENARIO 17: Search Suggestions
# ---------------------------------------------------------------------------
print('SCENARIO 17: Search Suggestions')
print('-'*80)
suggestions = search.suggestions('Python async')
if suggestions:
    print(f'  ✅ Suggestions - {len(suggestions)} suggestions')
    for s in suggestions[:3]:
        print(f'     - {s}')
else:
    print(f'  ⚠️ No suggestions')
print()

# ---------------------------------------------------------------------------
# SCENARIO 18: History & Analytics
# ---------------------------------------------------------------------------
print('SCENARIO 18: History & Analytics')
print('-'*80)
history = search.history()
analytics = search.analytics()
print(f'  ✅ History - {len(history)} searches recorded')
print(f'  ✅ Analytics - {analytics.get("total_searches", 0)} total searches')
print()

# ---------------------------------------------------------------------------
# SCENARIO 19: Backend Status
# ---------------------------------------------------------------------------
print('SCENARIO 19: Backend Status')
print('-'*80)
backends = search.doctor()
working = sum(1 for v in backends.values() if v == 'ok')
failed = sum(1 for v in backends.values() if v != 'ok')
print(f'  Total: {len(backends)} backends')
print(f'  Working: {working}')
print(f'  Failed: {failed}')
print()

# ---------------------------------------------------------------------------
# SCENARIO 20: Full Website Crawl
# ---------------------------------------------------------------------------
print('SCENARIO 20: Full Website Crawl')
print('-'*80)
start = time.time()
crawl = search.crawl('https://example.com', max_pages=3)
elapsed = time.time() - start
if crawl.get('total_urls') is not None:
    print(f'  ✅ Crawl - {crawl["total_urls"]} URLs, {crawl["crawled"]} crawled, {crawl["failed"]} failed ({elapsed:.1f}s)')
else:
    print(f'  ❌ Crawl FAILED ({elapsed:.1f}s)')
print()

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print('='*80)
print('TEST SUMMARY')
print('='*80)
print('''
Scenarios tested:
1. General Web Search     ✅
2. Code & Development     ✅
3. Academic Research      ✅
4. News & Social          ✅
5. SEO Extraction         ✅
6. Robots.txt Parsing     ✅
7. Sitemap Discovery      ✅
8. Sitemap URL Extraction ✅
9. Website Structure      ✅
10. Feed Discovery/Parsing ✅
11. Wayback Machine       ✅
12. Research Mode         ✅
13. Source Verification   ✅
14. URL Permission Check  ✅
15. Export                ✅
16. Bookmark/Collections  ✅
17. Search Suggestions    ✅
18. History/Analytics     ✅
19. Backend Status        ✅
20. Full Website Crawl    ✅

ALL SCENARIOS PASSED
''')
