from __future__ import annotations

import json
import os
from typing import Any

from agents._anthropic import MODEL_SONNET, ask_json, load_prompt


def draft_email(*, name: str, category: str, city: str | None, preview_url: str, usp: list[str]) -> dict[str, str]:
    payload = {
        "name": name,
        "category": category,
        "city": city,
        "preview_url": preview_url,
        "usp": usp,
        "sender_name": os.environ.get("CONTACT_NAME", "Tomáš Obzina"),
        "sender_phone": os.environ.get("CONTACT_PHONE", ""),
        "sender_email": os.environ.get("GMAIL_SENDER", ""),
    }

    system = load_prompt("email_cz")
    result = ask_json(
        model=MODEL_SONNET,
        system=system,
        user=json.dumps(payload, ensure_ascii=False),
        max_tokens=1500,
        temperature=0.8,
    )

    subject = result.get("subject", f"Ukázka webu pro {name}")
    body = result.get("body", "")
    return {"subject": subject, "body": body}
