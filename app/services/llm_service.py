"""LLM extraction service."""
from __future__ import annotations

import json
import os
import asyncio
from typing import Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)


EXTRACTION_SYSTEM_PROMPT = """You are a Samsung Device Troubleshooting Extraction Engine.
Extract the troubleshooting plan ONLY using facts provided in the reference text.

STRICT SCHEMA & PHRASING RULES:
1. goal: Exact syntax: "Follow these steps to perform this <Topic> Troubleshooting"
2. title: Exactly 2 to 3 words, sentence case, identifying the core issue.
3. actionName: Title Case. One action per distinct physical screen or feature.
4. description: Exactly 5 to 7 words, starting with "It will", explaining the concrete benefit.
5. steps: Clear, imperative UI steps. One physical interaction per step. NO URLs or external links.
6. category: "auto", "manual", or "critical".

You MUST return a JSON object exactly matching this structure:
{
  "contexts": [
    {
      "goal": "Follow these steps to perform this Display Issues Troubleshooting",
      "title": "Display Issues",
      "score": 0.95,
      "actions": [
        {
          "actionName": "Screen Troubleshooting",
          "description": "It will attempt to revive display.",
          "category": "manual",
          "stepGroups": [
            {
              "steps": [
                "Press and hold Power and Volume Down for 10 seconds.",
                "Check if device vibrates.",
                "Plug device into official charger and wait 15 minutes."
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
    if not siis_response or not siis_response.strip():
        return {
            "query_variations": [query],
            "contexts": [],
            "fallback": "no_match",
            "model": MODEL_NAME,
            "cost_usd": 0.0
        }

    paraphrase_task = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": PARAPHRASE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Complaint: {query}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    extraction_task = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"User Complaint: {query}\n\nReference Text (SIIS): {siis_response}\n\nExtract the JSON payload. Ensure the root key is 'contexts'."}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    try:
        paraphrase_response, extraction_response = await asyncio.gather(paraphrase_task, extraction_task)
    except Exception as e:
        print(f"\n[CRITICAL LLM API ERROR] {e}")
        return {"query_variations": [query], "contexts": [], "fallback": "api_error", "model": MODEL_NAME, "cost_usd": 0.0}

    try:
        variations = json.loads(paraphrase_response.choices[0].message.content).get("query_variations", [])
    except Exception:
        variations = [query]

    try:
        extraction_data = json.loads(extraction_response.choices[0].message.content)
        contexts = extraction_data.get("contexts", [])
    except Exception:
        contexts = []

    total_tokens = paraphrase_response.usage.total_tokens + extraction_response.usage.total_tokens
    return {
        "query_variations": variations,
        "contexts": contexts,
        "model": MODEL_NAME,
        "cost_usd": round((total_tokens / 1000) * 0.00015, 5)
    }