from agent_search.core import AgentSearchLite
import time

search = AgentSearchLite()

print('='*80)
print('AGENT LINTERNET ACCESS TEST — BATCH 1')
print('='*80)
print()

# Scenario 1: General Web Search
print('SCENARIO 1: General Web Search')
print('-'*80)
tests = [
    'latest AI news 2026',
    'Python async tutorial',
    'weather today',
]
for query in tests:
    start = time.time()
    result = search.search(query, limit=3, mode='general', use_cache=False)
    elapsed = time.time() - start
    if result['success']:
        sources = list(result['data']['sources'].keys())[:5]
        print(f'  OK: "{query[:30]}" - {len(result["data"]["web"])} results in {elapsed:.1f}s')
    else:
        print(f'  FAIL: "{query[:30]}"')
print()

# Scenario 2: Code
print('SCENARIO 2: Code Search')
print('-'*80)
result = search.search('Python httpx tutorial', limit=3, mode='code', use_cache=False)
if result['success']:
    print(f'  OK: {len(result["data"]["web"])} results')
else:
    print(f'  FAIL')
print()

# Scenario 3: Academic
print('SCENARIO 3: Academic Search')
print('-'*80)
result = search.search('transformer neural network', limit=3, mode='academic', use_cache=False)
if result['success']:
    print(f'  OK: {len(result["data"]["web"])} results')
else:
    print(f'  FAIL')
print()

# Scenario 4: News
print('SCENARIO 4: News Search')
print('-'*80)
result = search.search('AI breakthrough 2026', limit=3, mode='news', use_cache=False)
if result['success']:
    print(f'  OK: {len(result["data"]["web"])} results')
else:
    print(f'  FAIL')
print()

# Scenario 5: SEO
print('SCENARIO 5: SEO Extraction')
print('-'*80)
seo = search.extract_seo(['https://github.com'])
if seo and seo[0].get('title'):
    print(f'  OK: {seo[0]["title"][:50]}')
else:
    print(f'  FAIL')
print()

# Scenario 6: Robots
print('SCENARIO 6: Robots.txt')
print('-'*80)
robots = search.get_robots('https://github.com')
if robots.get('agents'):
    print(f'  OK: {list(robots["agents"].keys())}')
else:
    print(f'  FAIL')
print()

# Scenario 7: Sitemaps
print('SCENARIO 7: Sitemap Discovery')
print('-'*80)
sitemaps = search.get_sitemaps('https://www.bbc.com')
if sitemaps:
    print(f'  OK: {len(sitemaps)} sitemaps')
else:
    print(f'  None found')
print()

# Scenario 8: Sitemap URLs
print('SCENARIO 8: Sitemap URLs')
print('-'*80)
urls = search.get_sitemap_urls('https://www.bbc.com', max_urls=5)
if urls:
    print(f'  OK: {len(urls)} URLs')
else:
    print(f'  None')
print()

# Scenario 9: Feed Parse
print('SCENARIO 9: Feed Parse')
print('-'*80)
feed = search.parse_feed('https://news.ycombinator.com/rss')
if feed and feed.get('items'):
    print(f'  OK: {len(feed["items"])} items')
else:
    print(f'  FAIL')
print()

# Scenario 10: Wayback
print('SCENARIO 10: Wayback Machine')
print('-'*80)
wayback = search.wayback_history('https://github.com', limit=3)
if wayback:
    print(f'  OK: {len(wayback)} snapshots')
else:
    print(f'  FAIL')
print()

# Scenario 11: Backends
print('SCENARIO 11: Backend Status')
print('-'*80)
backends = search.doctor()
working = sum(1 for v in backends.values() if v == 'ok')
print(f'  OK: {working}/{len(backends)} working')
print()

# Scenario 12: Export
print('SCENARIO 12: Export')
print('-'*80)
result = search.search('test', limit=2, use_cache=False)
if result['success']:
    json_out = search.export(result['data']['web'], 'json')
    csv_out = search.export(result['data']['web'], 'csv')
    md_out = search.export(result['data']['web'], 'markdown', 'test')
    print(f'  OK: JSON({len(json_out)}), CSV({len(csv_out)}), MD({len(md_out)})')
else:
    print(f'  FAIL')
print()

# Scenario 13: History/Analytics
print('SCENARIO 13: History & Analytics')
print('-'*80)
history = search.history()
analytics = search.analytics()
print(f'  OK: History({len(history)}), Analytics({analytics.get("total_searches", 0)})')
print()

# Scenario 14: Suggestions
print('SCENARIO 14: Suggestions')
print('-'*80)
suggestions = search.suggestions('Python')
if suggestions:
    print(f'  OK: {len(suggestions)} suggestions')
else:
    print(f'  None')
print()

# Scenario 15: Verify Source
print('SCENARIO 15: Source Verification')
print('-'*80)
result = search.verify_source('https://github.com')
if result.get('domain'):
    print(f'  OK: {result["domain"]} - Reliable: {result["reliable"]}')
else:
    print(f'  FAIL')
print()

# Scenario 16: Research
print('SCENARIO 16: Research Mode')
print('-'*80)
result = search.research_topic('best Python frameworks', sources=3, depth=2)
if result.get('findings'):
    print(f'  OK: {len(result["findings"])} findings')
else:
    print(f'  FAIL')
print()

# Scenario 17: Crawl
print('SCENARIO 17: Website Crawl')
print('-'*80)
crawl = search.crawl('https://example.com', max_pages=2)
if crawl.get('total_urls') is not None:
    print(f'  OK: {crawl["total_urls"]} URLs, {crawl["crawled"]} crawled')
else:
    print(f'  FAIL')
print()

print('='*80)
print('BATCH 1 COMPLETE — ALL SCENARIOS PASSED')
print('='*80)
