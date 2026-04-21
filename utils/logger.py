from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(event: str, **fields) -> None:
    record = {"ts": _now(), "event": event, **fields}
    print(json.dumps(record, ensure_ascii=False, default=str), flush=True)


def log_error(event: str, exc: BaseException, **fields) -> dict:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    payload = {"ts": _now(), "event": event, "error": str(exc), "traceback": tb, **fields}
    print(json.dumps(payload, ensure_ascii=False, default=str), file=sys.stderr, flush=True)
    return payload
