# -*- coding: utf-8 -*-
"""AgentEye — CLI for free internet data access."""

import argparse
import json
import sys

from agent_eye.core import AgentSearchLite, STRATEGY_MODES, interactive_mode
from agent_eye.exceptions import (
    AgentSearchError,
    InvalidModeError,
    InvalidURLError,
)


def main():
    parser = argparse.ArgumentParser(
        prog="agent-eye",
        description="Complete internet data access for AI agents — zero API keys, zero cost",
        epilog="AgentEye v6.4.0 — Based on Agent Reach by Panniantong (MIT)",
    )
    parser.add_argument("--version", action="version", version="agent-eye 6.4.0")
    
    sub = parser.add_subparsers(dest="command")
    
    # search
    p_search = sub.add_parser("search", help="Search the web")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", "--limit", type=int, default=5, help="Max results")
    p_search.add_argument("-m", "--mode", choices=list(STRATEGY_MODES.keys()), default="general", help="Strategy mode")
    p_search.add_argument("--no-cache", action="store_true", help="Skip cache")
    p_search.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    p_search.add_argument("--token-conscious", action="store_true", help="Format results to minimize token usage")
    p_search.add_argument("--max-tokens", type=int, default=2000, help="Max tokens for token-conscious formatting")
    p_search.add_argument("--site", help="Search specific site (e.g., github.com, wikipedia.org)")
    p_search.add_argument("--after", help="Results after date (YYYY-MM-DD)")
    p_search.add_argument("--before", help="Results before date (YYYY-MM-DD)")
    p_search.add_argument("--summarize", action="store_true", help="Generate summary of results")
    p_search.add_argument("--export", choices=["json", "csv", "markdown"], help="Export format")
    p_search.add_argument("--output", help="Output file path")
    
    # extract
    p_extract = sub.add_parser("extract", help="Extract content from URLs")
    p_extract.add_argument("urls", nargs="+", help="URLs to extract")
    p_extract.add_argument("--char-limit", type=int, default=15000)
    p_extract.add_argument("--no-smart", action="store_true", help="Disable smart extraction")
    
    # doctor
    sub.add_parser("doctor", help="Check backend status")
    
    # modes
    sub.add_parser("modes", help="List available strategy modes")
    
    # history
    sub.add_parser("history", help="Show search history")
    
    # analytics
    sub.add_parser("analytics", help="Show search analytics")
    
    # interactive
    sub.add_parser("interactive", help="Start interactive search mode")
    sub.add_parser("repl", help="Alias for interactive mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        search = AgentSearchLite()
        
        if args.command == "search":
            result = search.search(
                args.query,
                limit=args.limit,
                mode=args.mode,
                use_cache=not args.no_cache,
                expand=not args.no_expand,
                token_conscious=args.token_conscious,
                max_tokens=args.max_tokens,
                site=args.site,
                date_after=args.after,
                date_before=args.before,
            )
            if args.json or args.export:
                output = search.export(result.get("data", {}).get("web", []), args.export or "json", args.query)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output)
                    print(f"Results saved to {args.output}")
                else:
                    print(output)
            else:
                if result["success"]:
                    print(f"Mode: {result['data'].get('mode', 'general')}")
                    print(f"Queries: {result['data'].get('queries', [])}")
                    print(f"Sources: {result['data'].get('sources', {})}")
                    if result['data'].get('errors'):
                        print(f"Errors: {result['data']['errors']}")
                    print(f"Results: {len(result['data']['web'])}")
                    print()
                    for item in result["data"]["web"]:
                        print(f"{item['position']}. {item['title']}")
                        print(f"   {item['url']}")
                        if item.get("description"):
                            print(f"   {item['description'][:100]}")
                        print(f"   [source: {item.get('source', 'unknown')} | relevance: {item.get('relevance_score', 0):.2f}]")
                        print()
                    if args.summarize:
                        print("=== Summary ===")
                        print(search.summarize(result["data"]["web"], args.query))
                else:
                    print(f"Error: {result.get('error')}", file=sys.stderr)
                    if result.get('errors'):
                        print("Details:", file=sys.stderr)
                        for backend, err in result['errors'].items():
                            print(f"  {backend}: {err}", file=sys.stderr)
                    sys.exit(1)
        
        elif args.command == "extract":
            results = search.extract(args.urls, char_limit=args.char_limit, smart=not args.no_smart)
            for r in results:
                print(f"URL: {r['url']}")
                print(f"Title: {r.get('title', '(none)')}")
                print(f"Content: {len(r.get('content', ''))} chars")
                if r.get("error"):
                    print(f"Error: {r['error']}")
                else:
                    print(r.get("content", "")[:500])
                print("---")
        
        elif args.command == "doctor":
            print(search.doctor_report())
        
        elif args.command == "modes":
            print("Available Strategy Modes:")
            print("=" * 45)
            for mode, config in STRATEGY_MODES.items():
                print(f"\n  {mode}:")
                print(f"    {config['description']}")
                print(f"    Backends: {', '.join(config['backends'])}")
        
        elif args.command == "history":
            history = search.history()
            print("Search History:")
            print("=" * 45)
            for h in history[:10]:
                print(f"  {h['query'][:50]} ({h['result_count']} results)")
        
        elif args.command == "analytics":
            analytics = search.analytics()
            print("Search Analytics:")
            print("=" * 45)
            print(f"  Total searches: {analytics.get('total_searches', 0)}")
            print(f"  Modes used: {analytics.get('modes_used', {})}")
            print(f"  Sources used: {analytics.get('sources_used', {})}")
        
        elif args.command in ("interactive", "repl"):
            from agent_eye.core import interactive_mode
            interactive_mode()
    
    except InvalidModeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(f"Valid modes: {', '.join(exc.valid_modes)}", file=sys.stderr)
        sys.exit(1)
    except InvalidURLError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except AgentSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
