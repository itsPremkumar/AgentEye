# -*- coding: utf-8 -*-
"""Agent Search Lite — CLI for free web search."""

import argparse
import json
import sys

from agent_search.core import AgentSearchLite, STRATEGY_MODES
from agent_search.exceptions import (
    AgentSearchError,
    InvalidModeError,
    InvalidURLError,
)


def main():
    parser = argparse.ArgumentParser(
        prog="agent-search-lite",
        description="Free web search + content extraction for AI agents",
        epilog="Agent Search Lite v2.1.0 — Based on Agent Reach by Panniantong (MIT)",
    )
    parser.add_argument("--version", action="version", version="agent-search-lite 2.1.0")
    
    sub = parser.add_subparsers(dest="command")
    
    # search
    p_search = sub.add_parser("search", help="Search the web")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", "--limit", type=int, default=5, help="Max results")
    p_search.add_argument("-m", "--mode", choices=list(STRATEGY_MODES.keys()), default="general", help="Strategy mode")
    p_search.add_argument("--no-cache", action="store_true", help="Skip cache")
    p_search.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    
    # extract
    p_extract = sub.add_parser("extract", help="Extract content from URLs")
    p_extract.add_argument("urls", nargs="+", help="URLs to extract")
    p_extract.add_argument("--char-limit", type=int, default=15000)
    
    # doctor
    sub.add_parser("doctor", help="Check backend status")
    
    # modes
    sub.add_parser("modes", help="List available strategy modes")
    
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
            )
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
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
                        print(f"   [source: {item.get('source', 'unknown')}]")
                        print()
                else:
                    print(f"Error: {result.get('error')}", file=sys.stderr)
                    if result.get('errors'):
                        print("Details:", file=sys.stderr)
                        for backend, err in result['errors'].items():
                            print(f"  {backend}: {err}", file=sys.stderr)
                    sys.exit(1)
        
        elif args.command == "extract":
            results = search.extract(args.urls, char_limit=args.char_limit)
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
