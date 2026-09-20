"""Rules and output formatting service for PRISM (Member 4 - Validation QA)."""
from __future__ import annotations

from typing import Any
from validator import StrictValidator


async def sanitize_output(steps: dict[str, Any]) -> dict[str, Any]:
    """Validate and clean the final plan before it is cached and returned.

    Enforces:
    - Gate G5: ZERO URL leaks across all fields
    - Block A1: Goal format regex, Title 2-3 words, Description 5-7 words, Score 0.0-1.0
    - Block A2: Deeplink fallback to bixby://dummy_positive, action sorting (auto -> manual -> critical)
    - Block A5: Query variations strictly 8 to 10 items
    """
    if not isinstance(steps, dict):
        return steps

    query = steps.get("query", "")
    return StrictValidator.sanitize_plan(steps, query=query)
