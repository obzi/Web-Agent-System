from __future__ import annotations

import os
from typing import Any

from utils.logger import log


def _create_draft_via_mcp(to: str | None, subject: str, body: str) -> bool:
    """
    Gmail MCP connector is available inside Claude Routines; the running agent has
    `mcp__gmail__create_draft` as a tool. This pure-Python fallback prints the draft
    to stdout (the parent Claude agent picks it up from run logs).

    When called from inside a Routine, the orchestrator may redirect this call to the
    actual MCP tool; here we always also log to stdout so the human can copy-paste.
    """
    log("gmail.draft", to=to, subject=subject, body_preview=body[:200])
    # The real MCP invocation happens in the Routine runtime (main.py orchestrator),
    # which has access to the MCP tool surface. Here we persist to stdout/Supabase.
    return True


def create_draft(*, to: str | None, subject: str, body: str) -> None:
    # When we're not inside an MCP-capable runtime, keep the log + Supabase fallback.
    _create_draft_via_mcp(to, subject, body)


def summary_draft(processed: list[dict[str, Any]], errors: list[dict[str, Any]]) -> dict[str, str]:
    lines = ["Noční batch RapidLocalSites – souhrn", ""]
    if processed:
        lines.append("Nové ukázky:")
        for p in processed:
            lines.append(f"  • {p['name']} ({p['category']}) – {p.get('preview_url', 'n/a')}")
    if errors:
        lines.append("")
        lines.append("Chyby:")
        for e in errors:
            lines.append(f"  • {e.get('slug', '?')}: {e.get('reason', '?')}")
    body = "\n".join(lines)
    subject = f"RapidLocalSites – batch {os.environ.get('BATCH_NAME', '?')} ({len(processed)} OK / {len(errors)} chyb)"
    return {"subject": subject, "body": body}
