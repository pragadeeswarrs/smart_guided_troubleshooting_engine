from __future__ import annotations

import time
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import cache_manager
from app.schemas import APIResponse, MetaData, TroubleshootRequest
from app.services.llm_service import MODEL_NAME, extract_troubleshooting_steps
from app.services.search_service import map_deeplinks
from app.services.validation import sanitize_output
from app.retrieval import RetrievalEngine

# Initialize hybrid search engine at startup
retrieval_engine = RetrievalEngine(data_path="data/deeplinks.json")
app = FastAPI(title="PRISM Smart Guided Troubleshooting Engine", version="0.1.0")

# Wide open for hackathon use so the UI can be served from file:// or any port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _build_response(query: str, plan: dict[str, Any], meta: MetaData) -> APIResponse:
    return APIResponse(
        query=query,
        query_variations=plan.get("query_variations", []),
        response={"contexts": plan.get("contexts", [])},
        meta=meta,
    )


def _auto_find_siis_context(query: str) -> str | None:
    """Context finder that ignores punctuation and common filler words."""
    import os, json
    paths_to_try = [
        "siis_responses.json", 
        "data/siis_responses.json", 
        "Theme02_Input_Kit/student_kit/siis_responses.json",
        "participant-kit/Theme02_Input_Kit/student_kit/siis_responses.json",
        "../siis_responses.json"
    ]
    
    incoming_q = query.strip().lower()
    
    # Aggressively remove all punctuation
    for char in ".,!?'\"-":
        incoming_q = incoming_q.replace(char, "")
        
    filler_words = {"my", "the", "on", "is", "in", "and", "to", "a", "for", "with", "galaxy", "s24", "ultra", "plus", "phone", "device", "of", "it", "at", "i", "not", "working", "issue", "issues", "when", "during", "no", "keeps", "since", "latest"}
    incoming_words = {w for w in incoming_q.split() if w not in filler_words}
    
    print(f"\n[DEBUG] Searching context for query: {query}")

    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get("responses", [])
                    
                    for item in items:
                        stored_q = item.get("query", "").strip().lower()
                        if not stored_q:
                            stored_q = item.get("original_query", "").strip().lower()
                            
                        for char in ".,!?'\"-":
                            stored_q = stored_q.replace(char, "")
                            
                        stored_words = {w for w in stored_q.split() if w not in filler_words}
                        overlap = incoming_words.intersection(stored_words)
                        
                        if len(overlap) >= 2:
                            print(f"[DEBUG] Successfully matched query to: {stored_q[:50]}...")
                            siis_data = item.get("siis_response", "")
                            if isinstance(siis_data, dict):
                                return siis_data.get("content", str(siis_data))
                            return str(siis_data)
            except Exception as e:
                print(f"[DEBUG] Error reading {path}: {e}")
                
    print("[DEBUG] WARNING: No matching context found! Falling back to None.")
    return None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/troubleshoot", response_model=APIResponse, response_model_exclude_none=True)
async def troubleshoot(request: TroubleshootRequest) -> APIResponse:
    start = time.perf_counter()
    query = request.query.strip()
    
    # Get siis_response from request, OR auto-load it from local JSON files
    siis_response = getattr(request, "siis_response", None)
    if not siis_response:
        siis_response = _auto_find_siis_context(query)

    # Fast path: cache hit
    cached = cache_manager.get_cached_plan(query)
    if cached is not None:
        meta = MetaData(
            latency_ms=_elapsed_ms(start),
            cache_hit=True,
            model=cached.get("_model", MODEL_NAME),
            cost_usd=0.0,
        )
        return _build_response(query, cached, meta)

    # Slow path: extract -> map deeplinks -> validate
    plan = await extract_troubleshooting_steps(query, siis_response)
    plan = await map_deeplinks(plan)
    plan = await sanitize_output(plan)

    cache_manager.set_cached_plan(query, {**plan, "_model": plan.get("model", MODEL_NAME)})

    meta = MetaData(
        latency_ms=_elapsed_ms(start),
        cache_hit=False,
        model=plan.get("model", MODEL_NAME),
        cost_usd=float(plan.get("cost_usd", 0.0)),
    )
    return _build_response(query, plan, meta)


@app.delete("/v1/cache")
async def clear_cache() -> dict[str, int]:
    """Demo helper: wipe the cache so you can show a miss then a hit."""
    return {"cleared": cache_manager.clear_cache()}


# Optional: serve the UI at http://127.0.0.1:8000/ui/
_UI_DIR = Path(__file__).resolve().parent.parent / "ui"
if _UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")