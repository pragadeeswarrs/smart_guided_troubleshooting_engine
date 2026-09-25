"""Deeplink retrieval service."""
from __future__ import annotations

from typing import Any
from app.retrieval import RetrievalEngine

# Initialize retrieval engine instance
retrieval_engine = RetrievalEngine(data_path="data/deeplinks.json")


async def map_deeplinks(steps: dict[str, Any]) -> dict[str, Any]:
    """Attach actionableDeeplink and validationDeeplink to each step."""
    
    items = steps.get("contexts") or steps.get("actions") or steps.get("steps") or []
    
    for item in items:
        query_text = (
            item.get("description") 
            or item.get("step") 
            or item.get("text") 
            or str(item)
        )
        
        # Query ChromaDB + BM25 hybrid search engine
        match = retrieval_engine.search_deeplink(query_text) or {}
        
        category = item.get("category") or match.get("category", "manual")
        item["category"] = category
        
        deeplink_uri = match.get("deeplink_uri")
        
        # Rule 4: If an auto action has no catalog match, assign bixby://dummy_positive
        if not deeplink_uri and category == "auto":
            deeplink_uri = "bixby://dummy_positive"
            
        # Rule 2: Copy masked URI verbatim into actionableDeeplink
        item["actionableDeeplink"] = deeplink_uri
        
        # Rule 3: Copy validation object verbatim into validationDeeplink if present
        validation_obj = match.get("validation")
        if validation_obj:
            item["validationDeeplink"] = validation_obj
        else:
            item["validationDeeplink"] = None

    # Sort steps by priority: auto -> manual -> critical
    if hasattr(retrieval_engine, "sort_actions_by_category") and items:
        sorted_items = retrieval_engine.sort_actions_by_category(items)
        if "contexts" in steps:
            steps["contexts"] = sorted_items
        elif "actions" in steps:
            steps["actions"] = sorted_items

    return steps
