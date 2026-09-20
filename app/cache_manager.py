"""Disk-backed cache for troubleshooting plans (the "fast path").

NOTE: Matching is currently EXACT-STRING (after light normalisation:
trim, collapse whitespace, lowercase).
# TODO: Member 3 (Retrieval Engineer) will upgrade this to semantic matching
# (embedding similarity) so "wifi not working" and "my internet won't connect"
# can hit the same cached plan. Keep the get/set signatures stable.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from diskcache import Cache

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache_dir"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h; tune as needed

_cache = Cache(str(CACHE_DIR))


def _make_key(query: str) -> str:
    """Normalise the query and hash it into a stable cache key."""
    normalised = re.sub(r"\s+", " ", query).strip().lower()
    return "plan:" + hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def get_cached_plan(query: str) -> dict[str, Any] | None:
    """Return the cached plan for `query`, or None on a miss."""
    return _cache.get(_make_key(query), default=None)


def set_cached_plan(query: str, data: dict[str, Any]) -> None:
    """Store a plan for `query` with a TTL."""
    _cache.set(_make_key(query), data, expire=CACHE_TTL_SECONDS)


def clear_cache() -> int:
    """Remove every cached plan. Handy for demos. Returns number of entries removed."""
    count = len(_cache)
    _cache.clear()
    return count
