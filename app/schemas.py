"""API contract for the Smart Guided Troubleshooting Engine.

Every teammate codes against these models. Changing a field here changes
the contract for the UI and all services, so agree on it as a team first.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TroubleshootRequest(BaseModel):
    """Incoming request body for POST /v1/troubleshoot."""

    query: str = Field(..., min_length=1, max_length=500, description="User complaint in natural language")


class MetaData(BaseModel):
    """Observability info returned with every response."""

    latency_ms: int = Field(..., ge=0, description="Server-side processing time")
    cache_hit: bool = Field(..., description="True if served from the cache fast path")
    model: str = Field(..., description="Model that produced the plan")
    cost_usd: float = Field(..., ge=0.0, description="Estimated LLM cost for this request (0.0 on cache hit)")


class APIResponse(BaseModel):
    """Strict response envelope.

    `response` is a dict containing a `contexts` array. Each context is one
    troubleshooting step, e.g.:
        {
          "stepId": "step-1",
          "title": "...",
          "description": "...",
          "actionableDeeplink": "bixby://..."   # optional / nullable
        }
    """

    query: str
    query_variations: list[str] = Field(default_factory=list)
    response: dict[str, Any] = Field(default_factory=lambda: {"contexts": []})
    meta: MetaData
