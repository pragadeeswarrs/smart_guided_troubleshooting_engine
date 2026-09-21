"""Deeplink retrieval service."""
from __future__ import annotations

from typing import Any
from app.retrieval import RetrievalEngine

# Initialize retrieval engine instance
retrieval_engine = RetrievalEngine(data_path="data/deeplinks.json")


async def map_deeplinks(steps: dict[str, Any]) -> dict[str, Any]:
    """Attach the correct `actionableDeeplink` to each step in `steps["contexts"]`."""
    
    # Get the list of steps/contexts from the payload
    items = steps.get("contexts") or steps.get("actions") or steps.get("steps") or []
    
    for item in items:
        # Extract the description string
        query_text = (
            item.get("description") 
            or item.get("step") 
            or item.get("text") 
            or str(item)
        )
        
        # Query ChromaDB + BM25 hybrid search engine
        match = retrieval_engine.search_deeplink(query_text)
        
        # Attach the matched deeplink URI and action category
        item["actionableDeeplink"] = match.get("deeplink_uri")
        item["category"] = match.get("category", "manual")
        
    # Sort steps by priority: auto -> manual -> critical
    if hasattr(retrieval_engine, "sort_actions_by_category") and items:
        sorted_items = retrieval_engine.sort_actions_by_category(items)
        if "contexts" in steps:
            steps["contexts"] = sorted_items
        elif "actions" in steps:
            steps["actions"] = sorted_items

    return steps
