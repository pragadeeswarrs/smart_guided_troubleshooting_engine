"""results_generator.py: Generates the official results.jsonl submission file.

Processes scenarios from data/siis_responses.json (or siis_responses.json).
Enforces:
- Gate G3: >= 95% of test queries covered (covers 100% of scenarios)
- Gate G4: >= 90% pass strict Pydantic validation (guarantees 100%)
- Gate G5: ZERO URL leaks across all lines
- Block A1: Structural rules (Goal regex, Title 2-3 words, Description 5-7 words, Score 0.0-1.0)
- Block A2: Deeplink rules (auto fallback to bixby://dummy_positive, auto->manual->critical sorting)
- Block A5: Strictly 8 to 10 query variations per entry
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.schemas import ContextDeeplinkResponse
from validator import StrictValidator, load_catalog_uris, scrub_urls


def find_data_file(filename: str) -> Path:
    """Locate dataset file in data/ or root directory."""
    candidates = [
        Path("data") / filename,
        Path(filename),
        Path(__file__).resolve().parent / "data" / filename,
        Path(__file__).resolve().parent / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(f"Cannot locate {filename} in data/ or current directory.")


def offline_extract_plan(query: str, siis_text: str) -> Dict[str, Any]:
    """Deterministic offline extractor converting SIIS text into structured contexts."""
    lines = [line.strip() for line in siis_text.splitlines() if line.strip()]
    header = lines[0] if lines else query

    # Extract topic
    topic_match = re.search(r"([A-Za-z\s]+?)(?:Troubleshooting|Issues|Optimization|Recovery|Cleanup|Detection):", header)
    topic = topic_match.group(1).strip() if topic_match else "Device"
    if not topic or len(topic.split()) > 2:
        topic = "Device"

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", siis_text)
    meaningful_sentences = [
        s.strip() for s in sentences if len(s.strip()) > 10 and not s.strip().startswith("#")
    ]

    actions: List[Dict[str, Any]] = []

    # 1. First action: auto settings configuration
    auto_steps = []
    for s in meaningful_sentences[:2]:
        cleaned_s = scrub_urls(s)
        if cleaned_s:
            auto_steps.append(cleaned_s)
    if not auto_steps:
        auto_steps = ["Navigate to Settings and verify current configuration."]

    actions.append({
        "actionName": f"{topic} Configuration".title(),
        "description": f"It will configure {topic.lower()} settings on device",
        "category": "auto",
        "stepGroups": [
            {
                "steps": auto_steps,
                "actionableDeeplink": {
                    "deeplink": "bixby://dummy_positive",
                    "description": f"It will open device {topic.lower()} settings",
                    "message": f"{topic} Settings",
                },
            }
        ],
    })

    # 2. Second action: manual user inspection
    if len(meaningful_sentences) > 2:
        manual_steps = [scrub_urls(s) for s in meaningful_sentences[2:4] if scrub_urls(s)]
        if manual_steps:
            actions.append({
                "actionName": f"{topic} Inspection".title(),
                "description": f"It will guide your manual hardware inspection",
                "category": "manual",
                "stepGroups": [{"steps": manual_steps, "actionableDeeplink": None}],
            })

    # 3. Third action: critical disruptive check if mentioned in text
    critical_keywords = ["reset", "wipe", "factory", "reboot", "restart", "recovery"]
    critical_sentences = [
        scrub_urls(s) for s in meaningful_sentences if any(k in s.lower() for k in critical_keywords)
    ]
    if critical_sentences:
        actions.append({
            "actionName": f"{topic} Recovery".title(),
            "description": f"It will perform device recovery and reboot",
            "category": "critical",
            "stepGroups": [{"steps": [critical_sentences[0]], "actionableDeeplink": None}],
        })

    title = f"{topic} Settings"
    goal = f"Follow these steps to perform this {topic} Troubleshooting."

    return {
        "query": query,
        "query_variations": [],
        "contexts": [
            {
                "title": title,
                "goal": goal,
                "score": 0.95,
                "actions": actions,
            }
        ],
    }


async def generate_submission(
    siis_file: str = "siis_responses.json",
    output_file: str = "results.jsonl",
    use_live_llm: bool = False,
) -> None:
    """Generate results.jsonl from input scenarios."""
    print("=" * 60)
    print("PRISM RESULTS GENERATOR (Member 4 - Release Gatekeeper)")
    print("=" * 60)

    siis_path = find_data_file(siis_file)
    print(f"Reading input scenarios from: {siis_path}")

    with open(siis_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios", list(scenarios.values()))

    total_scenarios = len(scenarios)
    print(f"Total scenarios loaded: {total_scenarios}")

    catalog_uris = load_catalog_uris()
    print(f"Loaded catalog URIs: {len(catalog_uris)}")

    # Check if live LLM is requested and configured
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    if use_live_llm and has_groq:
        from app.services.llm_service import extract_troubleshooting_steps
        print("Using live LLM extraction pipeline via Groq API.")
    else:
        print("Using deterministic offline PRISM extraction engine.")

    results: List[Dict[str, Any]] = []
    schema_passed = 0
    url_leaks_count = 0

    for idx, item in enumerate(scenarios, start=1):
        query = item.get("query", "").strip()
        siis_text = item.get("siis_response", "").strip()

        if use_live_llm and has_groq:
            try:
                raw_plan = await extract_troubleshooting_steps(query, siis_text)
            except Exception as e:
                print(f"  [Scenario {idx}] LLM error ({e}), falling back to deterministic extractor.")
                raw_plan = offline_extract_plan(query, siis_text)
        else:
            raw_plan = offline_extract_plan(query, siis_text)

        # Sanitize with StrictValidator
        sanitized = StrictValidator.sanitize_plan(raw_plan, query=query, catalog_uris=catalog_uris)

        # Enforce exact results.jsonl format
        submission_entry = {
            "query": query,
            "query_variations": sanitized["query_variations"],
            "response": {
                "contexts": sanitized["contexts"]
            },
        }

        # Validate Schema (Gate G4)
        try:
            ContextDeeplinkResponse(contexts=submission_entry["response"]["contexts"])
            schema_passed += 1
        except Exception as err:
            print(f"  [Scenario {idx}] Schema Validation Failed: {err}")

        # Audit URL leaks (Gate G5)
        leaks = StrictValidator.audit_url_leaks(submission_entry)
        if leaks:
            url_leaks_count += len(leaks)
            print(f"  [Scenario {idx}] Gate G5 Leak: {leaks}")

        # Check variations count (Block A5)
        var_count = len(submission_entry["query_variations"])
        assert 8 <= var_count <= 10, f"Scenario {idx} query_variations must be 8-10, got {var_count}"

        results.append(submission_entry)

    # Write out results.jsonl
    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("\n" + "-" * 60)
    print("SUBMISSION VERIFICATION REPORT")
    print("-" * 60)
    coverage_pct = (len(results) / total_scenarios) * 100 if total_scenarios else 0
    schema_pct = (schema_passed / len(results)) * 100 if results else 0

    print(f"Output File:           {out_path.resolve()}")
    print(f"Total Entries:         {len(results)} / {total_scenarios}")
    print(f"Gate G3 (Coverage):    {coverage_pct:.1f}% (Target: >= 95%) -> {'[PASS]' if coverage_pct >= 95 else '[FAIL]'}")
    print(f"Gate G4 (Schema QA):   {schema_pct:.1f}% (Target: >= 90%) -> {'[PASS]' if schema_pct >= 90 else '[FAIL]'}")
    print(f"Gate G5 (URL Leaks):   {url_leaks_count} leaks (Target: 0)  -> {'[PASS]' if url_leaks_count == 0 else '[FAIL]'}")
    print(f"Block A5 (Variations): 100% of entries have 8-10 variations -> [PASS]")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(generate_submission())
