from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass


ANIMATIONS = ["scroll-reveal", "parallax", "fade-stagger", "typewriter", "static"]
CARD_STYLES = ["flat", "elevated", "bordered", "gradient"]


@dataclass(frozen=True)
class DesignSeed:
    hero_variant: str
    palette_shift: str
    optional_sections_order: list[str]
    animation: str
    card_style: str

    def to_dict(self) -> dict:
        return asdict(self)


def _bytes(slug: str) -> bytes:
    return hashlib.sha256(slug.encode("utf-8")).digest()


def _pick(seed: bytes, offset: int, choices: list[str]) -> str:
    if not choices:
        return ""
    return choices[seed[offset % len(seed)] % len(choices)]


def _shuffle(seed: bytes, offset: int, items: list[str]) -> list[str]:
    if len(items) <= 1:
        return list(items)
    arr = list(items)
    for i in range(len(arr) - 1, 0, -1):
        j = seed[(offset + i) % len(seed)] % (i + 1)
        arr[i], arr[j] = arr[j], arr[i]
    return arr


def make_seed(slug: str, hero_variants: list[str], palette_shifts: list[str], optional_section_ids: list[str]) -> DesignSeed:
    """Deterministic pick of design variants inside a category skeleton."""
    b = _bytes(slug)
    return DesignSeed(
        hero_variant=_pick(b, 0, hero_variants),
        palette_shift=_pick(b, 4, palette_shifts),
        optional_sections_order=_shuffle(b, 8, optional_section_ids),
        animation=_pick(b, 16, ANIMATIONS),
        card_style=_pick(b, 20, CARD_STYLES),
    )
