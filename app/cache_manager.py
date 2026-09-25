from typing import Any, Optional

class SimpleCacheManager:
    def __init__(self):
        self.cache: dict[str, Any] = {}

    def get_cached_plan(self, query: str) -> Optional[Any]:
        return self.cache.get(query)

    def set_cached_plan(self, query: str, plan: Any) -> None:
        self.cache[query] = plan

    def clear_cache(self) -> int:
        cleared = len(self.cache)
        self.cache.clear()
        return cleared

cache_manager = SimpleCacheManager()

def get_cached_plan(query: str):
    return cache_manager.get_cached_plan(query)

def set_cached_plan(query: str, plan: Any):
    cache_manager.set_cached_plan(query, plan)

def clear_cache():
    return cache_manager.clear_cache()