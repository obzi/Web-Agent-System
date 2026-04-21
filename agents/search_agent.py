from __future__ import annotations

import os
from typing import Any

import httpx
from slugify import slugify

from utils.logger import log


GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


# Query bank per region; every run picks one per call with random rotation via ts seed.
QUERIES = [
    '"salon" OR "kadeřnictví" OR "nehty" site:instagram.com "{region}"',
    '"restaurace" OR "bistro" OR "kavárna" site:instagram.com "{region}"',
    '"autoservis" OR "pneuservis" OR "instalatér" site:facebook.com "{region}"',
    '"fitness" OR "jóga" OR "pilates" site:instagram.com "{region}"',
    '"cukrárna" OR "pekárna" OR "rukodělná" site:instagram.com "{region}"',
    '"účetní" OR "právník" OR "poradce" site:firmy.cz "{region}"',
    '"masáže" OR "fyzio" OR "ordinace" site:facebook.com "{region}"',
]


def search_candidates(region: str, count: int, excluded_slugs: set[str]) -> list[dict[str, Any]]:
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not cx:
        log("search.skip", reason="missing google credentials")
        return []

    seen: set[str] = set(excluded_slugs)
    collected: list[dict[str, Any]] = []

    with httpx.Client(timeout=20.0) as http:
        for template in QUERIES:
            if len(collected) >= count:
                break
            query = template.format(region=region)
            try:
                resp = http.get(
                    GOOGLE_CSE_URL,
                    params={"key": api_key, "cx": cx, "q": query, "num": 10},
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])
            except Exception as exc:  # noqa: BLE001
                log("search.query_failed", query=query, error=str(exc))
                continue

            for item in items:
                name = (item.get("title") or "").split("|")[0].split(" - ")[0].strip()
                if not name:
                    continue
                slug = slugify(f"{name}-{region}")
                if slug in seen:
                    continue
                seen.add(slug)
                collected.append({
                    "name": name,
                    "city": region,
                    "profile_url": item.get("link"),
                    "source": _source(item.get("link", "")),
                    "slug": slug,
                    "snippet": item.get("snippet"),
                })
                if len(collected) >= count:
                    break
    log("search.candidates", region=region, found=len(collected))
    return collected


def _source(url: str) -> str:
    if "instagram.com" in url:
        return "instagram"
    if "facebook.com" in url:
        return "facebook"
    if "firmy.cz" in url:
        return "firmy.cz"
    if "maps" in url:
        return "maps"
    return "other"
