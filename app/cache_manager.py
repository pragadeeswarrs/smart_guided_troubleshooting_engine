"""Disk-backed cache with Semantic Matching for troubleshooting plans.

Supports:
1. Exact & normalized string matching (< 5ms response time).
2. Paraphrase caching (all query_variations are indexed upon cache write).
3. Semantic / fuzzy similarity fallback for unseen query paraphrases (>= 80% target hit rate).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, List, Set, Tuple

from diskcache import Cache

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache_dir"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h

_cache = Cache(str(CACHE_DIR))
_INDEX_KEY = "meta:semantic_index"

# Synonyms/stem mapping for smartphone troubleshooting
_STEMS = {
    "display": "screen",
    "dark": "black",
    "blank": "black",
    "dead": "black",
    "shut": "off",
    "draining": "drain",
    "drains": "drain",
    "disconnecting": "disconnect",
    "disconnects": "disconnect",
    "dropping": "disconnect",
    "drops": "disconnect",
    "unresponsive": "freeze",
    "freezing": "freeze",
    "freezes": "freeze",
    "crashing": "crash",
    "crashes": "crash",
    "overheating": "heat",
    "warm": "heat",
    "hot": "heat",
    "restarting": "reboot",
    "restarts": "reboot",
}


def _normalise(text: str) -> str:
    """Strip punctuation, collapse whitespace, and lowercase."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _make_key(query: str) -> str:
    """Normalise the query and hash it into a stable cache key."""
    return "plan:" + hashlib.sha256(_normalise(query).encode("utf-8")).hexdigest()


def _tokenize(text: str) -> Set[str]:
    """Extract stemmed informative word tokens."""
    stops = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "is", "it", "my", "me", "how", "do", "i", "your", "with", "this", "that", "and", "or"}
    words = _normalise(text).split()
    tokens = set()
    for w in words:
        if len(w) > 1 and w not in stops:
            stemmed = _STEMS.get(w, w)
            tokens.add(stemmed)
    return tokens


def _similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """Compute token Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union > 0 else 0.0


def _get_semantic_index() -> List[Tuple[str, str, List[str]]]:
    """Retrieve indexed queries: [(cache_key, query_text, tokens)]."""
    return _cache.get(_INDEX_KEY, default=[])


def _update_semantic_index(key: str, text: str):
    """Add a query to the semantic index."""
    idx = _get_semantic_index()
    tokens = list(_tokenize(text))
    # Deduplicate index entries
    filtered = [entry for entry in idx if entry[0] != key]
    filtered.append((key, text, tokens))
    _cache.set(_INDEX_KEY, filtered, expire=CACHE_TTL_SECONDS)


def get_cached_plan(query: str) -> dict[str, Any] | None:
    """Return the cached plan for `query`, or None on a miss."""
    exact_key = _make_key(query)
    cached = _cache.get(exact_key, default=None)
    if cached is not None:
        return cached

    # Semantic / Paraphrase fallback
    query_tokens = _tokenize(query)
    if not query_tokens:
        return None

    best_key = None
    best_sim = 0.0

    index_entries = _get_semantic_index()
    for key, indexed_text, token_list in index_entries:
        sim = _similarity(query_tokens, set(token_list))
        if sim > best_sim:
            best_sim = sim
            best_key = key

    # If semantic similarity is >= 0.20, treat as semantic cache hit
    if best_sim >= 0.20 and best_key:
        matched = _cache.get(best_key, default=None)
        if matched is not None:
            return matched

    return None


def set_cached_plan(query: str, data: dict[str, Any]) -> None:
    """Store a plan for `query` and all of its query variations."""
    primary_key = _make_key(query)
    _cache.set(primary_key, data, expire=CACHE_TTL_SECONDS)
    _update_semantic_index(primary_key, query)

    # Index each variation from query_variations so paraphrases immediately hit cache
    for variation in data.get("query_variations", []):
        var_str = str(variation)
        var_key = _make_key(var_str)
        _cache.set(var_key, data, expire=CACHE_TTL_SECONDS)
        _update_semantic_index(var_key, var_str)


def clear_cache() -> int:
    """Remove every cached plan. Returns number of entries removed."""
    count = len(_cache)
    _cache.clear()
    return count
