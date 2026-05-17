"""
Generate newsletter content using Groq (free tier), given web research results.

Usage:
    python tools/generate_newsletter_content.py
        --topic "AI agents in healthcare"
        [--audience "technical founders"]
        [--tone "informed but conversational"]
        [--search-results .tmp/search_results.json]
        [--article-texts .tmp/article_texts.json]

Outputs structured JSON to .tmp/newsletter_content.json.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv
from json_repair import repair_json

load_dotenv()

SYSTEM_PROMPT = """You are an expert newsletter writer. You produce high-quality, well-researched newsletters that are engaging, fact-dense, and visually structured.

Your newsletters follow this section structure:
1. **Subject line** — punchy, specific, curiosity-driving (max 60 chars)
2. **Preview text** — the sentence shown in inbox previews (max 90 chars)
3. **Hook intro** — 2-3 sentences that grab attention with a surprising fact or framing
4. **Main piece** — the core 400-600 word deep-dive, written in clear paragraphs
5. **Key stats** — 3-5 bullet points, each a specific number or data point from the research
6. **Quick insights** — 3 short "did you know" style bullets
7. **Sources** — list of article titles + URLs used as research
8. **Closing CTA** — one sentence inviting a reply or reflection

You also produce SVG infographics to go with the newsletter:
- 2-3 SVGs total
- Each SVG is self-contained, 600px wide, with appropriate height
- Use a clean, modern design: dark background (#1a1a2e), accent color (#e94560), white text
- Types to create: stat callout card, key takeaways visual, or mini-timeline
- SVGs must use inline styles only (no external CSS)
- CRITICAL: In SVG code, use ONLY single quotes for all attribute values — never double quotes inside SVG, as it will break the JSON encoding

Return your response as a single valid JSON object with this exact structure:
{
  "subject": "...",
  "preview_text": "...",
  "sections": {
    "hook_intro": "...",
    "main_piece": "...",
    "key_stats": ["...", "...", "..."],
    "quick_insights": ["...", "...", "..."],
    "sources": [{"title": "...", "url": "..."}],
    "closing_cta": "..."
  },
  "svgs": [
    {"label": "descriptive label", "code": "<svg>...</svg>"},
    {"label": "descriptive label", "code": "<svg>...</svg>"}
  ]
}

Ground all claims in the provided research. Do not invent statistics. If the research lacks a specific data point, say "research suggests" rather than citing a specific number.
Return ONLY the raw JSON object. Do not wrap it in markdown fences or add any text before or after it."""


def build_user_prompt(topic: str, audience: str, tone: str, search_results: list, article_texts: list) -> str:
    parts = [
        f"**Topic:** {topic}",
        f"**Target audience:** {audience}",
        f"**Tone:** {tone}",
        "",
        "---",
        "**Research: Search Results**",
    ]

    for i, r in enumerate(search_results, 1):
        parts.append(f"\n[{i}] {r['title']}")
        parts.append(f"URL: {r['url']}")
        if r.get("published_date"):
            parts.append(f"Date: {r['published_date']}")
        parts.append(r["snippet"][:300])

    if article_texts:
        parts.append("\n---\n**Research: Full Article Excerpts**")
        for a in article_texts[:4]:
            parts.append(f"\n### {a['title']} ({a['url']})")
            parts.append(a["text"][:1200])

    parts.append("\n---\nWrite the newsletter now. Return only the JSON object.")
    return "\n".join(parts)


def generate(topic: str, audience: str, tone: str, search_results: list, article_texts: list) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("ERROR: GROQ_API_KEY not set in .env — get a free key at https://console.groq.com", file=sys.stderr)
        sys.exit(1)

    client = Groq(api_key=api_key)
    user_prompt = build_user_prompt(topic, audience, tone, search_results, article_texts)

    print("Calling Groq (llama-3.3-70b-versatile) to generate newsletter content...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Use json-repair to fix common LLM issues (unescaped quotes in SVGs, trailing commas, etc.)
        try:
            return json.loads(repair_json(raw))
        except Exception as e:
            Path(".tmp/raw_llm_response.txt").write_text(raw, encoding="utf-8")
            raise ValueError(f"Model returned invalid JSON: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default="general professionals")
    parser.add_argument("--tone", default="informed but conversational")
    parser.add_argument("--search-results", default=".tmp/search_results.json")
    parser.add_argument("--article-texts", default=".tmp/article_texts.json")
    args = parser.parse_args()

    search_path = Path(args.search_results)
    if not search_path.exists():
        print(f"ERROR: search results not found at {search_path}. Run search_web.py first.", file=sys.stderr)
        sys.exit(1)

    search_results = json.loads(search_path.read_text(encoding="utf-8"))

    article_texts = []
    article_path = Path(args.article_texts)
    if article_path.exists():
        article_texts = json.loads(article_path.read_text(encoding="utf-8"))

    content = generate(args.topic, args.audience, args.tone, search_results, article_texts)

    out_path = Path(".tmp/newsletter_content.json")
    out_path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Newsletter content saved to {out_path}")
    print(f"Subject: {content.get('subject', '(none)')}")
    print(f"SVGs generated: {len(content.get('svgs', []))}")


if __name__ == "__main__":
    main()
