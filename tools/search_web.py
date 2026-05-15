"""
Search the web for a topic using Tavily and save results to .tmp/search_results.json.

Usage:
    python tools/search_web.py --topic "AI agents in healthcare" [--days-back 30] [--max-results 10]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def search(topic: str, days_back: int = 30, max_results: int = 10) -> list[dict]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "your_tavily_api_key_here":
        print("ERROR: TAVILY_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = TavilyClient(api_key=api_key)

    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    response = client.search(
        query=topic,
        search_depth="advanced",
        max_results=max_results,
        include_answer=True,
        include_raw_content=False,
    )

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            "published_date": r.get("published_date", ""),
            "score": r.get("score", 0),
        })

    # Sort by relevance score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Topic to search for")
    parser.add_argument("--days-back", type=int, default=30, help="Prefer content from last N days")
    parser.add_argument("--max-results", type=int, default=10, help="Max search results to return")
    args = parser.parse_args()

    print(f"Searching for: {args.topic}")
    results = search(args.topic, days_back=args.days_back, max_results=args.max_results)
    print(f"Found {len(results)} results")

    out_path = Path(".tmp/search_results.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
