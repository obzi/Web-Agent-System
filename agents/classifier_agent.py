from __future__ import annotations

import json
from typing import Any

from agents._anthropic import MODEL_HAIKU, ask_json, load_prompt
from utils.logger import log


ALLOWED_CATEGORIES = {
    "salon", "restaurace", "autoservis", "fitness",
    "remeslo", "sluzby_b2b", "zdravi", "eshop", "unknown",
}


def classify(scrape_data: dict[str, Any]) -> dict[str, Any]:
    system = load_prompt("classify")
    try:
        result = ask_json(
            model=MODEL_HAIKU,
            system=system,
            user=json.dumps(scrape_data, ensure_ascii=False),
            max_tokens=800,
            temperature=0.1,
        )
    except Exception as exc:  # noqa: BLE001
        log("classify.failed", error=str(exc))
        return {"status": "rozpracovane", "category": "unknown", "reason": f"classifier error: {exc}", "usp": []}

    status = result.get("status", "rozpracovane")
    if status not in {"ok", "rozpracovane", "nepouzitelne"}:
        status = "rozpracovane"
    category = result.get("category", "unknown")
    if category not in ALLOWED_CATEGORIES:
        category = "unknown"

    usp = result.get("usp") or []
    if not isinstance(usp, list):
        usp = []

    return {
        "status": status,
        "category": category,
        "reason": result.get("reason", ""),
        "usp": usp[:3],
    }
