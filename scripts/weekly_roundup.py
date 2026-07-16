#!/usr/bin/env python3
"""
Friday weekly roundup.

Reads the week's digests from data/news.json and asks Claude to synthesise the
threads that actually mattered. Adds a "roundup" entry to data/news.json.

Run:  python scripts/weekly_roundup.py
Env:  GEMINI_API_KEY
"""
import os, json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Make `from llm import ...` work whether llm.py sits beside this file (scripts/)
# or at the repo root — protects against upload mishaps.
_here = Path(__file__).resolve().parent
for _p in (str(_here), str(_here.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from llm import generate_json, have_key

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"


def main():
    if not NEWS.exists():
        print("No news.json yet."); return
    doc = json.loads(NEWS.read_text())

    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    week = [i for i in doc.get("issues", [])
            if i.get("type") == "digest" and i.get("date", "") >= since]
    if not week:
        print("No digests this week — skipping roundup."); return

    stories = []
    for issue in week:
        for it in issue.get("items", []):
            stories.append(f"- {it['title']} ({it['source']}): {it.get('summary','')}")
    listing = "\n".join(stories[:45])

    if not have_key():
        print("No GEMINI_API_KEY — skipping."); return

    prompt = f"""Below are this week's AI/tech stories from my digest.

Write a weekly roundup that identifies the 3 REAL threads of the week — not a list,
but the connective tissue. Be opinionated but grounded. Write in your own words.

Return JSON shaped exactly like:
{{
 "intro": "one sentence, max 28 words, framing the week",
 "themes": [
   {{"heading":"short punchy heading (max 6 words)","text":"2-3 sentences on this thread and why it matters to a practising data scientist"}}
 ],
 "tags": ["3-5 short lowercase tags"]
}}

Stories:
{listing}"""

    data = generate_json(prompt, max_tokens=1800)
    if not data:
        print("Roundup skipped — no usable response."); return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pretty = datetime.now(timezone.utc).strftime("%B %-d, %Y") if os.name != "nt" else today

    items = [{
        "title": t.get("heading", ""),
        "url": "",
        "source": "Weekly synthesis",
        "summary": t.get("text", ""),
        "tags": [],
    } for t in data.get("themes", [])]

    entry = {
        "type": "roundup",
        "date": today,
        "slug": f"roundup-{today}",
        "title": f"The Week in AI — {pretty}",
        "intro": data.get("intro", ""),
        "tags": data.get("tags", [])[:5],
        "items": items,
    }

    issues = [i for i in doc.get("issues", []) if i.get("slug") != entry["slug"]]
    issues.insert(0, entry)
    doc["issues"] = issues[:90]
    doc["updated"] = datetime.now(timezone.utc).isoformat()
    NEWS.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"Wrote roundup with {len(items)} themes")


if __name__ == "__main__":
    main()
