"""FastAPI entrypoint: app setup and routes only.

Business logic lives in app/services/*. Keep this file small so teammates
can work in their own service files without merge conflicts.
"""
from __future__ import annotations

import time
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

app = FastAPI(title="PRISM Smart Guided Troubleshooting Engine", version="0.1.0")

# Wide open for hackathon use so the UI can be served from file:// or any port.
# credentials must stay False when allow_origins is "*".
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/troubleshoot", response_model=APIResponse)
async def troubleshoot(request: TroubleshootRequest) -> APIResponse:
    start = time.perf_counter()
    query = request.query.strip()
    # 1. Retrieve siis_response from request if present
    siis_response = getattr(request, "siis_response", None)

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
    # 2. Pass siis_response to Member 2's extraction function
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


# Optional: serve the UI at http://127.0.0.1:8000/ui/ (avoids file:// issues).
_UI_DIR = Path(__file__).resolve().parent.parent / "ui"
if _UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
