"""
Flask web app for AI Newsletter Generator.

Run:
    python app.py

Then open http://localhost:5001
"""

import json
import sys
import uuid
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so we can import tools directly
sys.path.insert(0, str(Path(__file__).parent))
from tools.search_web import search as _search
from tools.fetch_article import fetch as _fetch
from tools.generate_newsletter_content import generate as _generate
from tools.render_newsletter_html import render as _render
from tools.send_email_gmail import send as _send, get_gmail_service
import os

app = Flask(__name__)

# job_id -> {step, msg, done, error}
jobs = {}


def run_pipeline(job_id: str, topic: str, audience: str, tone: str, email: str):
    def update(step, msg, done=False, error=None):
        jobs[job_id] = {"step": step, "msg": msg, "done": done, "error": error}

    tmp = Path(".tmp")
    tmp.mkdir(exist_ok=True)

    # Step 1: Search
    update(1, f'Searching the web for "{topic}"…')
    try:
        results = _search(topic, days_back=30, max_results=10)
        (tmp / "search_results.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        update(1, "Web search failed.", error=str(e))
        return

    # Step 2: Fetch top 2 articles (faster)
    update(2, "Reading top articles…")
    article_texts = []
    for r in results[:2]:
        try:
            text = _fetch(r["url"], timeout=10)
            if text:
                article_texts.append({"title": r["title"], "url": r["url"], "text": text[:1000]})
        except Exception:
            continue
    (tmp / "article_texts.json").write_text(
        json.dumps(article_texts, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Step 3: Generate content with AI
    update(3, "Generating newsletter with AI (~30s)…")
    try:
        content = _generate(topic, audience, "informed but conversational", results, article_texts)
        (tmp / "newsletter_content.json").write_text(
            json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except BaseException as e:
        update(3, "AI generation failed.", error=str(e))
        return

    # Step 4: Render HTML
    update(4, "Rendering HTML email…")
    try:
        html = _render(content, issue_number=1)
        (tmp / "newsletter_final.html").write_text(html, encoding="utf-8")
    except Exception as e:
        update(4, "Rendering failed.", error=str(e))
        return

    # Step 5: Send
    update(5, f"Sending to {email}…")
    try:
        subject = content.get("subject", f"Newsletter: {topic}")
        sender = os.getenv("GMAIL_SENDER", "")
        service = get_gmail_service()
        _send(html, subject, to=email, sender=sender)
    except Exception as e:
        update(5, "Email sending failed.", error=str(e))
        return

    update(5, f"Newsletter sent to {email}!", done=True)


@app.route("/")
def index():
    resp = app.make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/generate", methods=["POST"])
def generate():
    topic   = request.form.get("topic", "").strip()
    audience = request.form.get("audience", "general professionals").strip()
    tone    = request.form.get("tone", "informed but conversational").strip()
    email   = request.form.get("email", "").strip()

    if not topic or not email:
        return jsonify({"error": "Topic and email are required"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"step": 0, "msg": "Starting…", "done": False, "error": None}

    t = threading.Thread(
        target=run_pipeline,
        args=(job_id, topic, audience, tone, email),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False, threaded=True)
