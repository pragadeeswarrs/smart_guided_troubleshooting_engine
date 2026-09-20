"""Rules and output formatting service."""
from __future__ import annotations

from typing import Any


async def sanitize_output(steps: dict[str, Any]) -> dict[str, Any]:
    """Validate and clean the final plan before it is cached and returned.

    TODO: Member 4 (Validation QA): enforce schema rules, drop invalid or
    unsafe deeplinks, dedupe steps, and normalise wording.
    Currently returns the steps unaltered.
    """
    return steps
