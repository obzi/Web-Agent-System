from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from agents import (
    classifier_agent,
    email_drafter,
    github_agent,
    gmail_agent,
    scraper_agent,
    search_agent,
    vercel_agent,
    web_generator,
)
from utils import supabase_store
from utils.dedup import dedup_hash
from utils.logger import log, log_error


@dataclass
class PipelineResult:
    processed: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> int:
        return len(self.processed)

    @property
    def failed(self) -> int:
        return len(self.errors)


def _regions() -> list[str]:
    raw = os.environ.get("SEARCH_REGIONS", "Praha")
    return [r.strip() for r in raw.split(",") if r.strip()]


def _already_known_slugs() -> set[str]:
    # Pulling just slugs is cheap; dedup at candidate level saves scrape/classify cost.
    res = supabase_store.client().table("prospects").select("slug").execute()
    return {row["slug"] for row in (res.data or [])}


def _pick_new_candidates(count: int) -> list[dict[str, Any]]:
    excluded = _already_known_slugs()
    results: list[dict[str, Any]] = []
    for region in _regions():
        if len(results) >= count:
            break
        batch = search_agent.search_candidates(region, count=count - len(results), excluded_slugs=excluded)
        for candidate in batch:
            candidate["dedup_hash"] = dedup_hash(candidate["name"], None, candidate.get("city"))
            if supabase_store.find_prospect_by_hash(candidate["dedup_hash"]):
                log("pipeline.skip_dedup", slug=candidate["slug"])
                continue
            results.append(candidate)
            excluded.add(candidate["slug"])
            if len(results) >= count:
                break
    return results


def process_one(candidate: dict[str, Any], *, dry_run: bool = False, test_mode: bool = False) -> dict[str, Any]:
    slug = candidate["slug"]
    log("pipeline.start", slug=slug, name=candidate.get("name"))

    # scrape
    scraped = scraper_agent.scrape(candidate)

    # classify
    classification = classifier_agent.classify(scraped)
    log("pipeline.classify", slug=slug, status=classification["status"], category=classification["category"])

    if classification["status"] != "ok" and not test_mode:
        prospect = supabase_store.upsert_prospect({
            "slug": slug,
            "dedup_hash": candidate["dedup_hash"],
            "name": candidate.get("name"),
            "city": candidate.get("city"),
            "address": scraped.get("address"),
            "category": classification["category"],
            "status": classification["status"],
            "source_url": candidate.get("profile_url"),
            "error_reason": classification.get("reason"),
            "raw_scrape": scraped,
            "classification": classification,
        })
        return {"slug": slug, "status": classification["status"], "reason": classification.get("reason")}

    # build content for generator
    content = _compose_content(slug, candidate, scraped, classification)

    # generate (Opus)
    generated = web_generator.generate(slug=slug, category=classification["category"], content=content)
    if generated is None:
        supabase_store.upsert_prospect({
            "slug": slug,
            "dedup_hash": candidate["dedup_hash"],
            "name": candidate.get("name"),
            "city": candidate.get("city"),
            "category": classification["category"],
            "status": "rozpracovane",
            "source_url": candidate.get("profile_url"),
            "error_reason": "Opus quota exceeded; retry next run.",
            "raw_scrape": scraped,
            "classification": classification,
            "is_test": test_mode,
        })
        return {"slug": slug, "status": "rozpracovane", "reason": "Opus quota"}

    html = generated["html"]
    content_json = generated["content_json"]

    if dry_run:
        log("pipeline.dry_run", slug=slug, html_preview=html[:400])
        return {"slug": slug, "status": "dry_run", "html": html}

    # GitHub push
    repo_url = github_agent.push_site(slug, html, content_json)

    # Vercel deploy
    preview_url = vercel_agent.deploy_preview(slug)

    # Verify
    _verify(preview_url, candidate.get("name", ""))

    # Email draft (Sonnet)
    email = email_drafter.draft_email(
        name=candidate["name"],
        category=classification["category"],
        city=candidate.get("city"),
        preview_url=preview_url,
        usp=classification.get("usp", []),
    )
    subject = email["subject"]
    body = email["body"]
    if test_mode and not subject.startswith("[TEST]"):
        subject = f"[TEST] {subject}"

    # Gmail draft via MCP (or stdout fallback)
    gmail_agent.create_draft(to=None, subject=subject, body=body)

    # Persist
    prospect = supabase_store.upsert_prospect({
        "slug": slug,
        "dedup_hash": candidate["dedup_hash"],
        "name": candidate.get("name"),
        "city": candidate.get("city"),
        "address": scraped.get("address"),
        "category": classification["category"],
        "status": "delivered" if not test_mode else "new",
        "source_url": candidate.get("profile_url"),
        "preview_url": preview_url,
        "repo_url": repo_url,
        "raw_scrape": scraped,
        "classification": classification,
        "is_test": test_mode,
    })
    supabase_store.save_draft(prospect["id"], subject, body, scraped.get("email"))

    return {
        "slug": slug,
        "name": candidate["name"],
        "category": classification["category"],
        "status": "delivered",
        "preview_url": preview_url,
        "repo_url": repo_url,
        "subject": subject,
    }


def run_batch(count: int, *, dry_run: bool = False) -> PipelineResult:
    batch_name = os.environ.get("BATCH_NAME", "manual")
    run_id = supabase_store.start_run(batch_name)
    result = PipelineResult()
    try:
        candidates = _pick_new_candidates(count)
        log("pipeline.candidates", count=len(candidates), batch=batch_name)
        for candidate in candidates:
            try:
                outcome = process_one(candidate, dry_run=dry_run)
                if outcome.get("status") == "delivered":
                    result.processed.append(outcome)
                else:
                    result.errors.append({"slug": candidate["slug"], "reason": outcome.get("reason", outcome.get("status"))})
            except Exception as exc:  # noqa: BLE001
                err = log_error("pipeline.exception", exc, slug=candidate.get("slug"))
                result.errors.append({"slug": candidate.get("slug"), "reason": str(exc)})
                try:
                    supabase_store.upsert_prospect({
                        "slug": candidate["slug"],
                        "dedup_hash": candidate["dedup_hash"],
                        "name": candidate.get("name"),
                        "city": candidate.get("city"),
                        "status": "rozpracovane",
                        "error_reason": str(exc),
                        "source_url": candidate.get("profile_url"),
                    })
                except Exception:
                    pass

        # summary draft
        summary = gmail_agent.summary_draft(result.processed, result.errors)
        gmail_agent.create_draft(to=None, subject=summary["subject"], body=summary["body"])
    finally:
        supabase_store.finish_run(
            run_id,
            successes=result.ok,
            failures=result.failed,
            processed=[p.get("slug", "") for p in result.processed],
            errors=result.errors,
        )
    return result


def run_test(slug: str, *, dry_run: bool = False) -> dict[str, Any]:
    existing = supabase_store.get_prospect_by_slug(slug)
    if existing:
        candidate = {
            "slug": slug,
            "name": existing["name"],
            "city": existing.get("city"),
            "profile_url": existing.get("source_url"),
            "source": "test",
            "dedup_hash": existing["dedup_hash"],
        }
    else:
        name = slug.replace("-", " ").title()
        candidate = {
            "slug": slug,
            "name": name,
            "city": None,
            "profile_url": "",
            "source": "test",
            "dedup_hash": dedup_hash(name, None, None),
        }
    return process_one(candidate, dry_run=dry_run, test_mode=True)


def _compose_content(slug: str, candidate: dict, scraped: dict, classification: dict) -> dict[str, Any]:
    photos = scraped.get("photos") or []
    gallery = [
        {"url": p["url"], "alt": p.get("alt", ""), "type": p.get("type", "gallery")}
        for p in photos if isinstance(p, dict) and p.get("url")
    ]
    return {
        "slug": slug,
        "name": candidate.get("name") or scraped.get("name"),
        "category": classification["category"],
        "tagline": (classification.get("usp") or [""])[0],
        "usp": classification.get("usp", []),
        "about": scraped.get("bio") or scraped.get("services_text") or "",
        "services": scraped.get("services") or [],
        "menu": scraped.get("menu") or [],
        "schedule": scraped.get("schedule") or [],
        "team": scraped.get("team") or [],
        "pricing_tiers": scraped.get("pricing_tiers") or [],
        "process_steps": scraped.get("process_steps") or [],
        "faq": scraped.get("faq") or [],
        "reviews": scraped.get("reviews") or [],
        "gallery": gallery,
        "contact": {
            "phone": scraped.get("phone", ""),
            "email": scraped.get("email"),
            "address": scraped.get("address"),
            "city": candidate.get("city") or scraped.get("city"),
            "map_url": scraped.get("map_url"),
            "instagram": scraped.get("instagram"),
            "facebook": scraped.get("facebook"),
            "website": None,
        },
        "hours": scraped.get("hours") or {},
    }


def _verify(url: str, name: str) -> None:
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as http:
            resp = http.get(url)
            if resp.status_code != 200:
                log("verify.non_200", url=url, status=resp.status_code)
                return
            if name and name.lower()[:20] not in resp.text.lower():
                log("verify.name_missing", url=url)
    except Exception as exc:  # noqa: BLE001
        log("verify.error", url=url, error=str(exc))
