from __future__ import annotations

import json
from typing import Any

import httpx

from agents._anthropic import MODEL_HAIKU, ask_json, load_prompt
from utils.logger import log


_USER_AGENT = "Mozilla/5.0 (compatible; RapidLocalSitesBot/1.0)"


def fetch_profile_html(url: str) -> str:
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": _USER_AGENT}) as http:
            resp = http.get(url)
            resp.raise_for_status()
            return resp.text[:120_000]
    except Exception as exc:  # noqa: BLE001
        log("scrape.fetch_failed", url=url, error=str(exc))
        return ""


def scrape(candidate: dict[str, Any]) -> dict[str, Any]:
    """Fetch the candidate's profile and ask Haiku to extract structured data."""
    html = fetch_profile_html(candidate.get("profile_url", ""))
    user_payload = {
        "name": candidate.get("name"),
        "city": candidate.get("city"),
        "profile_url": candidate.get("profile_url"),
        "source": candidate.get("source"),
        "profile_html": html or "",
        "snippet": candidate.get("snippet"),
    }

    system = load_prompt("scrape")
    try:
        data = ask_json(
            model=MODEL_HAIKU,
            system=system,
            user=json.dumps(user_payload, ensure_ascii=False),
            max_tokens=3000,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        log("scrape.parse_failed", error=str(exc), slug=candidate.get("slug"))
        return {
            "name": candidate.get("name"),
            "city": candidate.get("city"),
            "phone": None,
            "photos": [],
            "reviews": [],
            "raw_notes": f"scrape failed: {exc}",
        }
    return data
