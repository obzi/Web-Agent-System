from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

from agents import vercel_agent
from utils import supabase_store
from utils.logger import log


def run_cleanup(force_ttl: int | None = None) -> dict[str, int]:
    ttl = force_ttl if force_ttl is not None else int(os.environ.get("PREVIEW_TTL_DAYS", "14"))
    cleaned_slugs = vercel_agent.cleanup_old_previews(ttl)
    for slug in cleaned_slugs:
        supabase_store.update_prospect(slug, {"status": "archived"})

    # 1x/week delete archived unusable older than 180 days (run on Monday).
    archived = 0
    if datetime.now(timezone.utc).weekday() == 0:
        archived = supabase_store.archive_unusable(older_than_days=180)
        log("cleanup.archive_unusable", archived=archived)

    return {"vercel_cleaned": len(cleaned_slugs), "unusable_archived": archived}
