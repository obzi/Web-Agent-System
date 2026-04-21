from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents._anthropic import MODEL_OPUS, ask_json, is_quota_error, load_prompt
from utils.design_seed import make_seed
from utils.logger import log


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _design_tokens() -> dict[str, Any]:
    return _load_json(TEMPLATES_DIR / "design_tokens.json")


def _layout(category: str) -> dict[str, Any]:
    path = TEMPLATES_DIR / "layouts" / f"{category}.json"
    if not path.exists():
        path = TEMPLATES_DIR / "layouts" / "sluzby_b2b.json"
    return _load_json(path)


def generate(*, slug: str, category: str, content: dict[str, Any]) -> dict[str, Any] | None:
    """Return dict with keys `html` and `content_json`, or None when quota exceeded."""
    tokens_all = _design_tokens()
    tokens = tokens_all.get(category) or tokens_all["sluzby_b2b"]
    layout = _layout(category)

    optional_ids = [s["id"] for s in layout.get("optional_sections", [])]
    seed = make_seed(
        slug=slug,
        hero_variants=tokens.get("hero_variants", [tokens.get("hero_type", "centered")]),
        palette_shifts=list(tokens.get("palette_shifts", {}).keys()) or ["default"],
        optional_section_ids=optional_ids,
    )

    payload = {
        "slug": slug,
        "category": category,
        "content": content,
        "design_tokens": tokens,
        "layout": layout,
        "design_seed": seed.to_dict(),
    }

    system = load_prompt("generate_web")
    try:
        result = ask_json(
            model=MODEL_OPUS,
            system=system,
            user=json.dumps(payload, ensure_ascii=False),
            max_tokens=16000,
            temperature=1.0,
        )
    except Exception as exc:  # noqa: BLE001
        if is_quota_error(exc):
            log("generate.quota", slug=slug, error=str(exc))
            return None
        raise

    if "html" not in result or "content_json" not in result:
        raise ValueError("Opus response missing html/content_json fields")
    return result
