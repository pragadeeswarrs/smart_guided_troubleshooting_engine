"""LLM extraction service.

Contract: return a dict shaped like
    {
      "query_variations": [str, ...],
      "contexts": [
          {"goal": str, "title": str, "actions": [...]},
          ...
      ],
      "fallback": "no_match" # (optional)
    }
"""
from __future__ import annotations

import json
import os
import asyncio
from typing import Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
import os

load_dotenv()

# 1. Use a highly stable Groq model
MODEL_NAME = "openai/gpt-oss-20b"
# 2. Point to the Groq server and use the GROQ_API_KEY
client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

EXTRACTION_SYSTEM_PROMPT = """You are a Samsung Device Troubleshooting Extraction Engine.
Extract the troubleshooting plan ONLY using facts provided in the reference text.

STRICT SCHEMA & PHRASING RULES:
1. goal: Exact syntax: "Follow these steps to perform this <Topic> Troubleshooting" (or Configuration).
2. title: Exactly 2 to 3 words, sentence case, identifying the core issue.
3. actionName: Title Case. One action per distinct physical screen or feature.
4. description: Exactly 5 to 7 words, starting with "It will", explaining the concrete benefit.
5. steps: Clear, imperative UI steps. One physical interaction per step. NO URLs or external links.
6. category: "auto" (standard configuration reachable via deeplink), "manual" (physical interventions), or "critical" (disruptive operations like reset, reboot, safe mode).

You MUST return a JSON object exactly matching this structure. Do not include deeplinks; they will be mapped later.
{
  "contexts": [
    {
      "goal": "Follow these steps to perform this...",
      "title": "...",
      "score": 0.95,
      "actions": [
        {
          "actionName": "...",
          "description": "It will...",
          "category": "auto",
          "stepGroups": [
            {
              "steps": [
                "Navigate to and open Settings.",
                "Tap on Display."
              ]
            }
          ]
        }
      ]
    }
  ]
}

If the reference text contains no viable troubleshooting steps, return {"contexts": []}.
"""

PARAPHRASE_SYSTEM_PROMPT = """Generate 8 to 10 distinct paraphrases of the input smartphone complaint.
Cover multiple registers: formal, casual, keyword-only, frustrated, and typo-inclusive.
Output strict JSON with a single key "query_variations" containing a list of strings.
"""

async def extract_troubleshooting_steps(query: str, siis_response: Optional[str] = None) -> dict[str, Any]:
    """Turn a user complaint and optional SIIS reference text into structured troubleshooting steps."""
    
    # 1. Fire off the paraphrase generation (Query Enrichment)
    paraphrase_task = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": PARAPHRASE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Complaint: {query}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    # 2. Fast-fail if no SIIS context is provided for extraction
    if not siis_response or not siis_response.strip():
        paraphrase_response = await paraphrase_task
        variations = json.loads(paraphrase_response.choices[0].message.content).get("query_variations", [])
        return {
            "query_variations": variations,
            "contexts": [],
            "fallback": "no_match",
            "model": MODEL_NAME,
            "cost_usd": 0.0
        }

    # 3. Fire off the structure extraction (Phase 1)
    extraction_task = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"User Complaint: {query}\n\nReference Text (SIIS): {siis_response}\n\nExtract the JSON payload. Ensure the root key is 'contexts'."}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    # 4. Await both calls simultaneously to slash cold-start latency
    paraphrase_response, extraction_response = await asyncio.gather(paraphrase_task, extraction_task)

    # 5. Parse and assemble
    try:
        variations = json.loads(paraphrase_response.choices[0].message.content).get("query_variations", [])
    except Exception:
        variations = [query]

    try:
        extraction_data = json.loads(extraction_response.choices[0].message.content)
        contexts = extraction_data.get("contexts", [])
    except Exception:
        contexts = []

    # Calculate approximate cost
    total_tokens = paraphrase_response.usage.total_tokens + extraction_response.usage.total_tokens
    cost = (total_tokens / 1000) * 0.00015 # gpt-4o-mini rough blended rate
    
    return {
        "query_variations": variations,
        "contexts": contexts,
        "model": MODEL_NAME,
        "cost_usd": round(cost, 5)
    }