"""LLM extraction service.

Contract: return a dict shaped like
    {
      "query_variations": [str, ...],
      "contexts": [
          {"stepId": str, "title": str, "description": str,
           "actionableDeeplink": str | None},
          ...
      ],
    }
"""
from __future__ import annotations

from typing import Any

MODEL_NAME = "mock-llm-v0"
# TODO: Member 2 (Prompt Engineer): report real model name / cost by extending
# the returned dict (e.g. "model", "cost_usd") and update main.py to read them.


async def extract_troubleshooting_steps(query: str) -> dict[str, Any]:
    """Turn a user complaint into structured troubleshooting steps.

    TODO: Member 2 (Prompt Engineer): replace this mock with real LLM
    extraction (prompting, structured output, query variation generation).
    """
    return {
        "query_variations": [
            f"{query} (rephrased)",
            f"how to fix: {query}",
        ],
        "contexts": [
            {
                "stepId": "step-1",
                "title": "Check battery usage",
                "description": "Open battery settings and look for apps using an unusual amount of power.",
                "actionableDeeplink": "bixby://settings/battery_usage",
            },
            {
                "stepId": "step-2",
                "title": "Restart your phone",
                "description": "Hold the side and volume-down buttons, then tap Restart.",
                "actionableDeeplink": None,
            },
            {
                "stepId": "step-3",
                "title": "Update your software",
                "description": "Install the latest software update to get recent fixes.",
                "actionableDeeplink": "bixby://settings/software_update",
            },
        ],
    }
