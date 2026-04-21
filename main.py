#!/usr/bin/env python3
"""RapidLocalSites CLI entrypoint (runs inside Claude Routines sandbox or locally)."""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agents import cleanup_agent, orchestrator
from utils.logger import log


def _require_env(names: list[str]) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        sys.exit(f"missing required env vars: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="rapidlocalsites")
    parser.add_argument("--batch", choices=["A", "B"], help="nightly batch name (sets BATCH_NAME env)")
    parser.add_argument("--count", type=int, default=2, help="number of prospects to process")
    parser.add_argument("--test", metavar="SLUG", help="run pipeline for a single slug (test mode)")
    parser.add_argument("--cleanup", action="store_true", help="run Vercel TTL cleanup + weekly archive")
    parser.add_argument("--force-ttl", type=int, help="override PREVIEW_TTL_DAYS for cleanup")
    parser.add_argument("--dry-run", action="store_true", help="skip GitHub push / Vercel / Gmail; print HTML")
    args = parser.parse_args()

    if args.batch:
        os.environ["BATCH_NAME"] = args.batch

    _require_env(["ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"])

    if args.cleanup:
        stats = cleanup_agent.run_cleanup(force_ttl=args.force_ttl)
        log("cli.cleanup", **stats)
        return 0

    if args.test:
        outcome = orchestrator.run_test(args.test, dry_run=args.dry_run)
        print(json.dumps(outcome, ensure_ascii=False, indent=2, default=str))
        return 0

    result = orchestrator.run_batch(args.count, dry_run=args.dry_run)
    print(json.dumps(
        {
            "batch": os.environ.get("BATCH_NAME", "manual"),
            "ok": result.ok,
            "failed": result.failed,
            "processed": result.processed,
            "errors": result.errors,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ))
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
