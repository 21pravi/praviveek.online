#!/usr/bin/env python3
"""
Shared LLM helper — Google Gemini.

All three bots call generate_json() from here, so the model and API wiring
live in exactly one place. Swap MODEL below to change every bot at once.

Env:  GEMINI_API_KEY   (set as a GitHub Actions secret — never hardcode it)
"""
import os
import json
import re
import sys

# gemini-3.1-flash-lite = Google's high-volume, cost-sensitive workhorse.
# Alternative: "gemini-3.5-flash" (smarter, pricier). Note gemini-2.0-flash
# was shut down on 2026-06-01 — don't use it.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")


def have_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def generate_json(prompt: str, max_tokens: int = 2000):
    """
    Send a prompt to Gemini and return parsed JSON, or None on any failure.

    Uses Gemini's JSON mode so the model can't wrap output in prose or
    markdown fences. Callers must handle None (no key, API down, bad JSON)
    and degrade gracefully rather than crash the workflow.
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("  ! No GEMINI_API_KEY set — skipping AI summaries", file=sys.stderr)
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("  ! google-genai not installed (pip install -r scripts/requirements.txt)",
              file=sys.stderr)
        return None

    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
                max_output_tokens=max_tokens,
            ),
        )
        raw = (resp.text or "").strip()
        if not raw:
            print("  ! Empty response from Gemini", file=sys.stderr)
            return None
        # JSON mode should make this unnecessary, but strip fences defensively.
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  ! Gemini call failed: {e}", file=sys.stderr)
        return None
