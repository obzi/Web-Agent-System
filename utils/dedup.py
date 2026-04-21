from __future__ import annotations

import hashlib
import unicodedata


def _norm(value: str | None) -> str:
    if not value:
        return ""
    stripped = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return "".join(ch.lower() for ch in stripped if ch.isalnum())


def dedup_hash(name: str, address: str | None = None, city: str | None = None) -> str:
    key = "|".join(filter(None, [_norm(name), _norm(address), _norm(city)]))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
