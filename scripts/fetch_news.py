#!/usr/bin/env python3
"""
Daily AI + tech digest bot.

Pulls headlines from RSS feeds, removes duplicates, keeps the most relevant
stories, and asks Claude to write a one-sentence original summary of each.
Writes data/news.json. Links always point back to the original source; we
never reproduce article text.

Run:  python scripts/fetch_news.py
Env:  GEMINI_API_KEY
"""
import os, json, re, sys, html
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
# Make `from llm import ...` work whether llm.py sits beside this file (scripts/)
# or at the repo root — protects against upload mishaps.
_here = Path(__file__).resolve().parent
for _p in (str(_here), str(_here.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from llm import generate_json, have_key

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news.json"

MAX_STORIES = 8                        # stories per digest
LOOKBACK_HOURS = 30
KEEP_ISSUES = 90                       # how many past digests to retain

# AI + general tech mix
FEEDS = [
    ("TechCrunch AI",      "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge",          "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica",       "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("VentureBeat AI",     "https://venturebeat.com/category/ai/feed/"),
    ("MIT Tech Review",    "https://www.technologyreview.com/feed/"),
    ("Google Research",    "https://research.google/blog/rss/"),
    ("OpenAI",             "https://openai.com/news/rss.xml"),
    ("Hacker News",        "https://hnrss.org/frontpage?points=250"),
    ("Engadget",           "https://www.engadget.com/rss.xml"),
]

# Stories mentioning these rank higher
BOOST = [
    "ai","artificial intelligence","llm","gpt","claude","gemini","openai","anthropic",
    "machine learning","neural","model","agent","rag","transformer","nvidia","chip",
    "data","research","funding","startup","launch","open source","benchmark","robot",
]

def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()

def collect():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    seen_urls, seen_titles, out = set(), set(), []

    for source, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  ! {source}: {e}", file=sys.stderr)
            continue

        for e in feed.entries[:25]:
            link = (e.get("link") or "").split("?")[0]
            title = clean(e.get("title"))
            if not link or not title:
                continue

            # published within lookback window?
            when = e.get("published_parsed") or e.get("updated_parsed")
            if when:
                dt = datetime(*when[:6], tzinfo=timezone.utc)
                if dt < cutoff:
                    continue
            else:
                dt = datetime.now(timezone.utc)

            nt = norm_title(title)
            if link in seen_urls or nt in seen_titles or len(nt) < 12:
                continue
            seen_urls.add(link); seen_titles.add(nt)

            blurb = clean(e.get("summary") or e.get("description") or "")[:600]
            hay = (title + " " + blurb).lower()
            score = sum(2 if k in title.lower() else 1 for k in BOOST if k in hay)

            out.append({
                "title": title, "url": link, "source": source,
                "blurb": blurb, "score": score, "when": dt.isoformat(),
            })

    out.sort(key=lambda x: (-x["score"], x["when"]), reverse=False)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:MAX_STORIES]


def summarize(stories):
    """One Gemini call: an original one-sentence summary per story."""
    if not have_key():
        for s in stories:
            s["summary"] = ""; s["tags"] = []
        return stories, ""

    listing = "\n\n".join(
        f"[{i}] TITLE: {s['title']}\nSOURCE: {s['source']}\nCONTEXT: {s['blurb'][:400]}"
        for i, s in enumerate(stories)
    )

    prompt = f"""You are writing a daily AI/tech digest for a data scientist's blog.

For each story below, write:
- "summary": ONE sentence (max 28 words), in your OWN words, explaining why it matters. Never copy phrasing from the source. Be concrete and neutral. No hype words like "game-changing".
- "tags": 1-2 short lowercase topic tags (e.g. "llm", "chips", "funding", "policy", "open source").

Then write "intro": one sentence (max 25 words) summarising the day's theme overall.

Stories:
{listing}

Return JSON shaped exactly like:
{{"intro":"...","summaries":[{{"i":0,"summary":"...","tags":["..."]}}]}}"""

    data = generate_json(prompt, max_tokens=2000)
    if not data:
        for s in stories:
            s.setdefault("summary", ""); s.setdefault("tags", [])
        return stories, ""

    by_i = {d["i"]: d for d in data.get("summaries", []) if "i" in d}
    for i, s in enumerate(stories):
        d = by_i.get(i, {})
        s["summary"] = d.get("summary", "")
        s["tags"] = d.get("tags", [])
    return stories, data.get("intro", "")


def main():
    print("Collecting stories…")
    stories = collect()
    if not stories:
        print("No fresh stories — nothing to publish.")
        return
    print(f"  {len(stories)} stories selected")

    stories, intro = summarize(stories)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pretty = datetime.now(timezone.utc).strftime("%B %-d, %Y") if os.name != "nt" else today

    issue = {
        "type": "digest",
        "date": today,
        "slug": f"digest-{today}",
        "title": f"AI & Tech Digest — {pretty}",
        "intro": intro,
        "tags": sorted({t for s in stories for t in s.get("tags", [])})[:5],
        "items": [
            {"title": s["title"], "url": s["url"], "source": s["source"],
             "summary": s["summary"], "tags": s.get("tags", [])}
            for s in stories
        ],
    }

    NEWS.parent.mkdir(parents=True, exist_ok=True)
    doc = {"updated": "", "issues": []}
    if NEWS.exists():
        try:
            doc = json.loads(NEWS.read_text())
        except Exception:
            pass

    issues = [i for i in doc.get("issues", []) if i.get("slug") != issue["slug"]]
    issues.insert(0, issue)
    doc["issues"] = issues[:KEEP_ISSUES]
    doc["updated"] = datetime.now(timezone.utc).isoformat()

    NEWS.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"Wrote {NEWS} — {len(issue['items'])} items")


if __name__ == "__main__":
    main()
