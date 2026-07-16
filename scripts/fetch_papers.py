#!/usr/bin/env python3
"""
arXiv paper picks.

Pulls recent cs.AI / cs.LG / cs.CL submissions, keeps the ones matching your
interests, and asks Claude to explain each in one plain-English sentence.
Writes data/papers.json.

Run:  python scripts/fetch_papers.py
Env:  GEMINI_API_KEY
"""
import os, json, re, sys, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
# Make `from llm import ...` work whether llm.py sits beside this file (scripts/)
# or at the repo root — protects against upload mishaps.
_here = Path(__file__).resolve().parent
for _p in (str(_here), str(_here.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from llm import generate_json, have_key

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "papers.json"

PICKS = 4          # papers per run
KEEP = 60          # total papers retained

# Tuned to your work — edit freely
INTERESTS = [
    "large language model", "retrieval augmented", "RAG", "churn",
    "customer segmentation", "recommendation", "time series",
    "agent", "fine-tuning", "embedding", "clustering", "tabular",
    "uplift modeling", "propensity", "telecom",
]

CATS = ["cs.AI", "cs.LG", "cs.CL"]
API = "http://export.arxiv.org/api/query?search_query={q}&sortBy=submittedDate&sortOrder=descending&max_results=60"


def clean(t):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or "")))
    return t.strip()


def collect():
    q = quote(" OR ".join(f"cat:{c}" for c in CATS))
    feed = feedparser.parse(API.format(q=q))
    rows = []
    for e in feed.entries:
        title = clean(e.get("title"))
        abstract = clean(e.get("summary"))
        if not title:
            continue
        hay = (title + " " + abstract).lower()
        score = sum(1 for k in INTERESTS if k.lower() in hay)
        if score == 0:
            continue
        rows.append({
            "title": title,
            "url": e.get("link"),
            "abstract": abstract[:900],
            "authors": ", ".join(a.get("name", "") for a in e.get("authors", [])[:3]) +
                       (" et al." if len(e.get("authors", [])) > 3 else ""),
            "date": (e.get("published") or "")[:10],
            "score": score,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:PICKS]


def summarize(rows):
    if not have_key() or not rows:
        for r in rows:
            r["summary"] = r["abstract"][:200]; r["tags"] = ["arxiv"]
        return rows

    listing = "\n\n".join(
        f"[{i}] TITLE: {r['title']}\nABSTRACT: {r['abstract'][:600]}"
        for i, r in enumerate(rows)
    )
    prompt = f"""For each arXiv paper below write:
- "summary": ONE plain-English sentence (max 30 words) in your own words — what they did and why a practising data scientist should care. No jargon-dumping, no copied phrasing.
- "tags": 1-2 short lowercase tags (e.g. "llm", "rag", "clustering").

Papers:
{listing}

Return JSON shaped exactly like:
{{"summaries":[{{"i":0,"summary":"...","tags":["..."]}}]}}"""

    data = generate_json(prompt, max_tokens=1500)
    if not data:
        for r in rows:
            r.setdefault("summary", r["abstract"][:200]); r.setdefault("tags", ["arxiv"])
        return rows

    by_i = {d["i"]: d for d in data.get("summaries", []) if "i" in d}
    for i, r in enumerate(rows):
        d = by_i.get(i, {})
        r["summary"] = d.get("summary", r["abstract"][:200])
        r["tags"] = d.get("tags", ["arxiv"])
    return rows


def main():
    rows = collect()
    if not rows:
        print("No matching papers today.")
        return
    rows = summarize(rows)

    doc = {"updated": "", "items": []}
    if OUT.exists():
        try:
            doc = json.loads(OUT.read_text())
        except Exception:
            pass

    have = {i["url"] for i in doc.get("items", [])}
    fresh = [{
        "title": r["title"], "url": r["url"], "date": r["date"],
        "summary": r["summary"], "authors": r["authors"],
        "tags": (r["tags"] + ["paper"])[:3],
    } for r in rows if r["url"] not in have]

    doc["items"] = (fresh + doc.get("items", []))[:KEEP]
    doc["updated"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT} — {len(fresh)} new papers")


if __name__ == "__main__":
    main()
