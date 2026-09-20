"""Deeplink retrieval service."""
from __future__ import annotations

from typing import Any


async def map_deeplinks(steps: dict[str, Any]) -> dict[str, Any]:
    """Attach the correct `actionableDeeplink` to each step in `steps["contexts"]`.

    TODO: Member 3 (Retrieval Engineer): implement vector search over the
    deeplink catalogue and fill `actionableDeeplink` for each context.
    Currently returns the steps unaltered.
    """
    return steps
