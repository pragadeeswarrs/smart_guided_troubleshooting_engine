import re
from typing import Any, Dict, List, Optional
import torch


def _normalize_query(q: str) -> str:
    """Normalize query by lowercasing and stripping punctuation/extra whitespace."""
    if not isinstance(q, str):
        return ""
    cleaned = re.sub(r"[^\w\s]", "", q.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _token_overlap_hit(q1: str, q2: str) -> bool:
    """Fast lexical similarity check for phrasing variations (e.g. 'phone freezing' vs 'phone still freezing')."""
    w1 = set(_normalize_query(q1).split())
    w2 = set(_normalize_query(q2).split())
    if not w1 or not w2:
        return False
    stop_words = {"the", "a", "an", "is", "my", "on", "in", "to", "for", "and", "it", "of", "with"}
    content_1 = w1 - stop_words
    content_2 = w2 - stop_words
    if len(content_1) >= 2 and content_1.issubset(content_2):
        return True
    if len(content_2) >= 2 and content_2.issubset(content_1):
        return True
    jaccard = len(content_1 & content_2) / max(1, len(content_1 | content_2))
    return jaccard >= 0.70


def is_dummy_plan(plan: Any) -> bool:
    """Detect if a plan is an error or the generic fallback."""
    if not isinstance(plan, dict):
        return True
    if plan.get("fallback") in ["api_error", "no_match"]:
        return True
    contexts = plan.get("contexts", [])
    if not contexts or not isinstance(contexts, list):
        return True
    # Check if this is the generic fallback dummy context ("Device Care diagnostics")
    for ctx in contexts:
        if not isinstance(ctx, dict):
            continue
        actions = ctx.get("actions", [])
        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("actionName") == "Device Care":
                for g in action.get("stepGroups", []):
                    if isinstance(g, dict) and any("run diagnostics" in str(s).lower() for s in g.get("steps", [])):
                        return True
    return False


class SemanticCacheManager:
    """Multi-tier Semantic Cache Manager combining exact, token overlap, and embedding similarity."""

    def __init__(self, semantic_threshold: float = 0.74):
        # Tier 1: Exact query match
        self.cache: Dict[str, Any] = {}
        # Tier 2: Normalized query & variations match
        self.normalized_cache: Dict[str, Any] = {}
        # Tier 3 & 4: Vector semantic embeddings
        self.semantic_threshold = semantic_threshold
        self._model = None
        self._all_embeddings: Optional[torch.Tensor] = None
        self._all_plans: List[Any] = []
        self._all_texts: List[str] = []

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from app.context_matcher import context_matcher
            if context_matcher and hasattr(context_matcher, "model") and context_matcher.model is not None:
                self._model = context_matcher.model
                return self._model
        except Exception:
            pass
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            return self._model
        except Exception as e:
            print(f"[WARN] SemanticCacheManager: Embedding model unavailable: {e}")
            return None

    def get_cached_plan(self, query: str) -> Optional[Any]:
        # 1. Tier 1: Exact query check (< 0.05ms)
        if query in self.cache:
            return self.cache[query]

        # 2. Tier 2: Normalized query check (< 0.1ms)
        norm_q = _normalize_query(query)
        if norm_q in self.normalized_cache:
            return self.normalized_cache[norm_q]

        # 3. Tier 3: Token subset overlap check (< 0.2ms)
        for cached_norm, plan in list(self.normalized_cache.items())[:60]:
            if _token_overlap_hit(norm_q, cached_norm):
                print(f"[DEBUG] Token Overlap Cache Hit: \"{query}\" ~ \"{cached_norm}\"")
                self.normalized_cache[norm_q] = plan
                return plan

        # 4. Tier 4: Dense Vector Semantic Similarity (< 5ms)
        if self._all_embeddings is not None and len(self._all_texts) > 0:
            model = self._get_model()
            if model is not None:
                try:
                    from sentence_transformers import util
                    query_emb = model.encode(query, convert_to_tensor=True)
                    similarities = util.cos_sim(query_emb, self._all_embeddings)[0]
                    best_idx = int(similarities.argmax())
                    best_score = float(similarities[best_idx])

                    if best_score >= self.semantic_threshold:
                        matched_plan = self._all_plans[best_idx]
                        print(f"[DEBUG] Semantic Vector Cache Hit: \"{query}\" ~ \"{self._all_texts[best_idx]}\" (Score: {best_score:.3f})")
                        self.normalized_cache[norm_q] = matched_plan
                        return matched_plan
                except Exception as e:
                    print(f"[WARN] SemanticCacheManager vector search error: {e}")

        return None

    def set_cached_plan(self, query: str, plan: Any) -> None:
        # GATE: NEVER CACHE DUMMY FALLBACK OR ERROR PLANS
        if is_dummy_plan(plan):
            return

        self.cache[query] = plan
        norm_q = _normalize_query(query)
        if norm_q:
            self.normalized_cache[norm_q] = plan

        # Index all query variations into normalized cache for instant hit
        variations: List[str] = []
        if isinstance(plan, dict):
            raw_vars = plan.get("query_variations", [])
            if isinstance(raw_vars, list):
                for v in raw_vars:
                    norm_v = _normalize_query(str(v))
                    if norm_v and norm_v not in self.normalized_cache:
                        self.normalized_cache[norm_v] = plan
                    if str(v).strip():
                        variations.append(str(v).strip())

        # Vector Indexing for dense semantic match
        model = self._get_model()
        if model is not None:
            try:
                texts_to_embed = [query]
                for v in variations[:6]:
                    if v.lower() != query.lower() and v not in texts_to_embed:
                        texts_to_embed.append(v)

                new_embs = model.encode(texts_to_embed, convert_to_tensor=True)
                if self._all_embeddings is None:
                    self._all_embeddings = new_embs
                else:
                    self._all_embeddings = torch.cat([self._all_embeddings, new_embs], dim=0)

                for t in texts_to_embed:
                    self._all_plans.append(plan)
                    self._all_texts.append(t)
            except Exception as e:
                print(f"[WARN] SemanticCacheManager vector indexing error: {e}")

    def clear_cache(self) -> int:
        cleared = len(self.cache) + len(self.normalized_cache)
        self.cache.clear()
        self.normalized_cache.clear()
        self._all_embeddings = None
        self._all_plans.clear()
        self._all_texts.clear()
        return cleared


# Backward compatible alias & singleton
SimpleCacheManager = SemanticCacheManager
cache_manager = SemanticCacheManager()

def get_cached_plan(query: str) -> Optional[Any]:
    return cache_manager.get_cached_plan(query)

def set_cached_plan(query: str, plan: Any) -> None:
    cache_manager.set_cached_plan(query, plan)

def clear_cache() -> int:
    return cache_manager.clear_cache()