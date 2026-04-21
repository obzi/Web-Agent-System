from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from utils.logger import log


_client: Client | None = None


def client() -> Client:
    global _client
    if _client is not None:
        return _client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    _client = create_client(url, key)
    return _client


# --- prospects --------------------------------------------------------------


def get_prospect_by_slug(slug: str) -> dict | None:
    res = client().table("prospects").select("*").eq("slug", slug).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def find_prospect_by_hash(dedup_hash: str) -> dict | None:
    res = client().table("prospects").select("id,slug,status").eq("dedup_hash", dedup_hash).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def upsert_prospect(row: dict[str, Any]) -> dict:
    res = client().table("prospects").upsert(row, on_conflict="dedup_hash").execute()
    return (res.data or [row])[0]


def update_prospect(slug: str, patch: dict[str, Any]) -> None:
    client().table("prospects").update(patch).eq("slug", slug).execute()


def list_new_prospects(limit: int) -> list[dict]:
    res = (
        client()
        .table("prospects")
        .select("*")
        .eq("status", "new")
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return res.data or []


def list_delivered_for_cleanup(older_than_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    res = (
        client()
        .table("prospects")
        .select("slug,preview_url,repo_url,updated_at")
        .eq("status", "delivered")
        .lt("updated_at", cutoff_iso)
        .execute()
    )
    return res.data or []


def archive_unusable(older_than_days: int) -> int:
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    res = (
        client()
        .table("prospects")
        .delete()
        .eq("status", "nepouzitelne")
        .lt("created_at", cutoff_iso)
        .execute()
    )
    return len(res.data or [])


# --- drafts -----------------------------------------------------------------


def save_draft(prospect_id: str, subject: str, body: str, to_email: str | None) -> None:
    client().table("drafts").insert({
        "prospect_id": prospect_id,
        "subject": subject,
        "body": body,
        "to_email": to_email,
        "sent": False,
    }).execute()


# --- runs -------------------------------------------------------------------


def start_run(batch_name: str) -> str:
    res = client().table("runs").insert({"batch_name": batch_name}).execute()
    return res.data[0]["id"]


def finish_run(run_id: str, *, successes: int, failures: int, processed: list[str], errors: list[dict] | None = None) -> None:
    client().table("runs").update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "successes": successes,
        "failures": failures,
        "processed_slugs": processed,
        "error_log": errors or [],
    }).eq("id", run_id).execute()
    log("run.finish", run_id=run_id, successes=successes, failures=failures)


# --- content / assets (used by deliver.py) ----------------------------------


def put_content(customer_id: str, slug: str, data: dict) -> None:
    client().table("content").upsert(
        {"customer_id": customer_id, "slug": slug, "data": data},
        on_conflict="slug",
    ).execute()


def put_assets(customer_id: str, slug: str, assets: list[dict]) -> None:
    if not assets:
        return
    rows = [
        {
            "customer_id": customer_id,
            "slug": slug,
            "url": a["url"],
            "alt": a.get("alt"),
            "type": a.get("type", "gallery"),
            "sort_order": idx,
        }
        for idx, a in enumerate(assets)
    ]
    client().table("assets").insert(rows).execute()


def create_customer(prospect_id: str, slug: str) -> str:
    res = client().table("customers").upsert(
        {"prospect_id": prospect_id, "slug": slug}, on_conflict="slug"
    ).execute()
    return res.data[0]["id"]
