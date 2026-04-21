#!/usr/bin/env python3
"""Run manually after a prospect signs:

1. Mark prospect status=signed.
2. Create a `customers` row + provision a content row in Supabase.
3. Upload assets rows from the prospect's raw_scrape.gallery.
4. (Optional) Print a magic-link URL the owner can use to log in and edit content.

Usage:
    python deliver.py --slug salon-krasa-praha --email owner@example.com
"""
from __future__ import annotations

import argparse
import json
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from utils import supabase_store
from utils.logger import log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--email", required=True, help="owner email for magic-link login")
    parser.add_argument("--domain", help="owner's domain (if known)")
    args = parser.parse_args()

    prospect = supabase_store.get_prospect_by_slug(args.slug)
    if not prospect:
        sys.exit(f"no prospect with slug={args.slug}")

    customer_id = supabase_store.create_customer(prospect["id"], args.slug)

    # Content from the generated content.json (persisted in Vercel repo).
    content_blob = prospect.get("raw_scrape") or {}
    classification = prospect.get("classification") or {}
    composed = {
        "slug": args.slug,
        "name": prospect.get("name"),
        "category": classification.get("category") or prospect.get("category"),
        "about": content_blob.get("bio"),
        "services": content_blob.get("services") or [],
        "menu": content_blob.get("menu") or [],
        "schedule": content_blob.get("schedule") or [],
        "team": content_blob.get("team") or [],
        "reviews": content_blob.get("reviews") or [],
        "contact": {
            "phone": content_blob.get("phone"),
            "email": args.email,
            "address": content_blob.get("address"),
            "instagram": content_blob.get("instagram"),
            "facebook": content_blob.get("facebook"),
            "website": args.domain,
        },
        "hours": content_blob.get("hours") or {},
        "usp": classification.get("usp", []),
    }
    supabase_store.put_content(customer_id, args.slug, composed)

    gallery = content_blob.get("photos") or []
    supabase_store.put_assets(customer_id, args.slug, [
        {"url": p.get("url"), "alt": p.get("alt"), "type": p.get("type", "gallery")}
        for p in gallery if isinstance(p, dict) and p.get("url")
    ])

    supabase_store.update_prospect(args.slug, {"status": "signed"})

    log("deliver.done", slug=args.slug, customer_id=customer_id)
    print(json.dumps({"customer_id": customer_id, "next": "send magic-link via Supabase Auth dashboard"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
