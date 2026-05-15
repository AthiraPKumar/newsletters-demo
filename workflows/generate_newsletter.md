# Workflow: Generate Newsletter

## Objective

Produce and email a polished, HTML-formatted newsletter with SVG infographics on any given topic, delivered to the configured Gmail inbox.

## Required Inputs

| Input | Required | Default | Notes |
|---|---|---|---|
| `topic` | Yes | — | The subject of the newsletter (e.g., "AI agents in healthcare") |
| `audience` | No | "general professionals" | Who is reading (shapes tone and depth) |
| `tone` | No | "informed but conversational" | Writing style |
| `days_back` | No | 30 | Prefer web content from the last N days |
| `max_results` | No | 10 | How many search results to retrieve |

## Step-by-Step Sequence

### Step 1 — Web Search

Run `tools/search_web.py` to gather current research on the topic.

```
python tools/search_web.py --topic "<topic>" [--days-back 30] [--max-results 10]
```

**Output:** `.tmp/search_results.json`

**Edge cases:**
- If Tavily returns fewer than 3 results, broaden the topic phrasing and retry once.
- If TAVILY_API_KEY is missing from `.env`, stop and ask the user to add it (free key at https://tavily.com).

---

### Step 2 — Deep-Fetch Top Articles (Optional but Recommended)

For the top 3–5 search results (highest `score` value), fetch the full article text to give Claude richer material.

For each URL, run:
```
python tools/fetch_article.py --url "<url>" --max-chars 8000
```

Collect the returned text alongside the article title and URL. Save the collection to `.tmp/article_texts.json` in this format:
```json
[
  {"title": "Article Title", "url": "https://...", "text": "..."}
]
```

**Edge cases:**
- If fetching a URL fails (timeout, 403, paywalled), skip it and move to the next — don't stop the workflow.
- If all fetches fail, continue to Step 3 using only the search snippets.

---

### Step 3 — Generate Newsletter Content

Run `tools/generate_newsletter_content.py` with the topic and all research.

```
python tools/generate_newsletter_content.py \
    --topic "<topic>" \
    --audience "<audience>" \
    --tone "<tone>"
```

The tool reads `.tmp/search_results.json` and `.tmp/article_texts.json` automatically.

**Output:** `.tmp/newsletter_content.json` containing:
- `subject` — email subject line
- `preview_text` — inbox preview sentence
- `sections` — all newsletter body sections
- `svgs` — 2–3 SVG infographic code strings

**Edge cases:**
- If Claude returns invalid JSON, check `.tmp/raw_claude_response.txt` and re-run.
- If `svgs` array is empty, the template renders without infographics — this is acceptable.

---

### Step 4 — Render HTML

Run `tools/render_newsletter_html.py` to produce the final email-ready HTML.

```
python tools/render_newsletter_html.py
```

**Output:** `.tmp/newsletter_final.html`

Open this file in a browser to visually verify the layout before sending.

---

### Step 5 — Send via Gmail

Run `tools/send_email_gmail.py` to deliver the newsletter.

```
python tools/send_email_gmail.py \
    --html .tmp/newsletter_final.html \
    --subject "<subject from newsletter_content.json>"
```

The tool sends to `GMAIL_SENDER` (your own address) by default.

**Edge cases:**
- If `token.json` is expired or missing, the tool will open a browser for OAuth re-authentication. Complete the flow and re-run.
- If `credentials.json` is missing, download it from Google Cloud Console (project → APIs & Services → Credentials → OAuth 2.0 Client → Download JSON).

---

## Expected Output

- Email arrives in the Gmail inbox at `GMAIL_SENDER`
- Subject matches the `subject` field from `newsletter_content.json`
- HTML renders with header, infographics, key stats section, quick insights, and sources

## Intermediary Files

All files in `.tmp/` are disposable — they are regenerated each time the workflow runs.

| File | Purpose |
|---|---|
| `.tmp/search_results.json` | Raw Tavily search results |
| `.tmp/article_texts.json` | Full article texts for deep research |
| `.tmp/newsletter_content.json` | Structured content + SVGs from Claude |
| `.tmp/newsletter_final.html` | Rendered email HTML |
| `.tmp/raw_claude_response.txt` | Only created on Claude JSON parse error |

## Improvement Log

_Document any quirks, rate limits, or better approaches discovered here so future runs benefit._

- (none yet)
