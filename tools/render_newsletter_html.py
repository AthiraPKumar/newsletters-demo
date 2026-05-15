"""
Render the final newsletter HTML from generated content JSON using Jinja2.

Usage:
    python tools/render_newsletter_html.py [--content .tmp/newsletter_content.json]
                                           [--output .tmp/newsletter_final.html]
                                           [--issue-number 1]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render(content: dict, issue_number: int = 1) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,  # SVG and HTML must not be escaped
    )
    template = env.get_template("newsletter.html.j2")

    sections = content.get("sections", {})
    hook_intro = sections.get("hook_intro", "")

    # Build sections_list from main_piece paragraphs, with generated titles
    main_piece = sections.get("main_piece", "")
    paragraphs = [p.strip() for p in main_piece.split("\n\n") if p.strip()]

    # Try to extract bold titles from paragraphs (e.g. **Meetings:** ...)
    sections_list = []
    for p in paragraphs:
        if p.startswith("**"):
            end = p.find("**", 2)
            if end != -1:
                title = p[2:end].rstrip(":")
                body = p[end + 2:].lstrip(": ").strip()
                sections_list.append({"title": title, "body": body})
            else:
                sections_list.append({"title": "Insight", "body": p})
        else:
            if sections_list:
                sections_list[-1]["body"] += " " + p
            else:
                sections_list.append({"title": "Overview", "body": p})

    # Hero stats — pull from key_stats or use defaults
    raw_stats = sections.get("key_stats", [])
    hero_stats = []
    for s in raw_stats[:3]:
        # Try to extract a leading number
        words = s.split()
        number = words[0] if words else "—"
        description = " ".join(words[1:]) if len(words) > 1 else s
        hero_stats.append({"number": number, "label": description[:30], "sublabel": ""})

    # Key stats for data grid
    key_stats = []
    for s in raw_stats:
        words = s.split()
        number = words[0] if words else "—"
        description = " ".join(words[1:]) if len(words) > 1 else s
        key_stats.append({"number": number, "description": description})

    # Sources byline (first 3 source names)
    sources = sections.get("sources", [])
    sources_byline = " & ".join(s["title"].split("—")[0].strip() for s in sources[:3])

    ctx = {
        "publication_name": "AI Ops Weekly",
        "publication_tagline": "Intelligence for Operators, Product Leaders & Tech Partners",
        "issue_number": issue_number,
        "issue_date": datetime.now().strftime("%A, %B %-d, %Y") if sys.platform != "win32"
                      else datetime.now().strftime("%A, %B %d, %Y").replace(" 0", " "),
        "subject": content.get("subject", ""),
        "preview_text": content.get("preview_text", ""),
        "headline": content.get("subject", ""),
        "deck": hook_intro[:200] + "…" if len(hook_intro) > 200 else hook_intro,
        "sources_byline": sources_byline or "multiple sources",
        "hero_stats": hero_stats,
        "hook_intro": hook_intro,
        "sections_list": sections_list,
        "pull_quote": sections.get("closing_cta", ""),
        "svgs": content.get("svgs", []),
        "key_stats": key_stats,
        "quick_insights": sections.get("quick_insights", []),
        "sources": sources,
        "closing_cta": sections.get("closing_cta", ""),
    }

    return template.render(**ctx)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", default=".tmp/newsletter_content.json")
    parser.add_argument("--output", default=".tmp/newsletter_final.html")
    parser.add_argument("--issue-number", type=int, default=1)
    args = parser.parse_args()

    content_path = Path(args.content)
    if not content_path.exists():
        print(f"ERROR: content file not found: {content_path}", file=sys.stderr)
        sys.exit(1)

    content = json.loads(content_path.read_text(encoding="utf-8"))
    html = render(content, issue_number=args.issue_number)

    out_path = Path(args.output)
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Newsletter HTML rendered to {out_path}")
    print(f"File size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
