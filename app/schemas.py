"""API contract for the Smart Guided Troubleshooting Engine.

This file MUST match the exact Pydantic schema provided in Appendix A
of the Samsung PRISM problem statement. The automated evaluation relies on 100% adherence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==========================================
# 1. Incoming Request Models
# ==========================================
class TroubleshootRequest(BaseModel):
    """Incoming request body for POST /v1/troubleshoot."""
    query: str = Field(..., min_length=1, max_length=500, description="User complaint in natural language")
    siis_response: Optional[str] = Field(None, description="Optional raw text context from knowledge base")


# ==========================================
# 2. Samsung PRISM Appendix A Contract Models
# ==========================================
class BaseDeeplink(BaseModel):
    deeplink: str

class Deeplink(BaseDeeplink):
    description: str
    message: Optional[str] = ""
    classes: Optional[Dict[str, str]] = None
    originalType: Optional[str] = None

class Condition(str, Enum):
    greater = "greater"
    equal = "equal"
    less = "less"

class ResultTypes(str, Enum):
    boolean = "boolean"
    intNum = "integer"
    string = "str"
    floatNum = "float"

class actionCategory(str, Enum):
    auto = "auto"
    manual = "manual"
    critical = "critical"

class ValidationDeepLink(BaseDeeplink):
    key: str
    resultType: Optional[ResultTypes] = None
    condition: Optional[Condition] = None
    value: Optional[str] = None

class StepGroup(BaseModel):
    steps: List[str]
    validationDeeplink: Optional[ValidationDeepLink] = None
    actionableDeeplink: Optional[Deeplink] = None

class Action(BaseModel):
    actionName: str
    description: str
    stepGroups: List[StepGroup]
    category: Optional[actionCategory] = actionCategory.manual

class Goal(BaseModel):
    goal: str
    title: str
    actions: List[Action]
    score: float

class ContextDeeplinkResponse(BaseModel):
    """RAG response containing a list of Goal objects."""
    contexts: List[Goal] = Field(default_factory=list)


# ==========================================
# 3. Final API Response Envelope
# ==========================================
class MetaData(BaseModel):
    """Observability info returned with every response."""
    latency_ms: int = Field(..., ge=0, description="Server-side processing time")
    cache_hit: bool = Field(..., description="True if served from the cache fast path")
    model: str = Field(..., description="Model that produced the plan")
    cost_usd: float = Field(..., ge=0.0, description="Estimated LLM cost for this request (0.0 on cache hit)")

class APIResponse(BaseModel):
    """Strict response envelope."""
    query: str
    query_variations: List[str] = Field(default_factory=list)
    response: ContextDeeplinkResponse = Field(default_factory=ContextDeeplinkResponse)
    meta: MetaData