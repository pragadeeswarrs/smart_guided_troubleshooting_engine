import asyncio
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.llm_service import extract_troubleshooting_steps
from app.schemas import ContextDeeplinkResponse

async def run_final_tests():
    print("=== SCENARIO 1: FULL EXTRACTION (Valid SIIS Text) ===")
    query = "My Samsung A115G tablet screen flashes and then goes completely blank whenever I tap to open an email in Gmail."
    siis_text = "Smartphone,Others Mobile,Tablet Email server not responding: # Troubleshooting Email Connection Issues\nIf you're having trouble accessing your email on your Samsung phone, here are some steps you can take to resolve the issue.\n## Step 1: Check Email Access on a PC\nFirst, try accessing your email on a personal computer."

    plan_full = await extract_troubleshooting_steps(query, siis_response=siis_text)

    # 1. Test Schema Compliance
    try:
        validated = ContextDeeplinkResponse(contexts=plan_full.get("contexts", []))
        print("✅ Schema Validation: PASS (Nested structure is strictly compliant)")
    except Exception as e:
        print("❌ Schema Validation: FAIL")
        print(e)

    # 2. Test Word Count & Phrasing Constraints
    contexts = plan_full.get("contexts", [])
    if contexts:
        for action in contexts[0].get("actions", []):
            desc = action.get("description", "")
            words = desc.split()
            if desc.startswith("It will") and 5 <= len(words) <= 7:
                print(f"✅ Description Constraint: PASS (\"{desc}\")")
            else:
                print(f"⚠️ Description Warning: '{desc}' (Length: {len(words)} words. Prompt drift detected.)")

    # 3. Test Paraphrases
    variations = plan_full.get("query_variations", [])
    if 8 <= len(variations) <= 10:
        print(f"✅ Query Variations: PASS (Generated {len(variations)} paraphrases)")
    else:
        print(f"⚠️ Query Variations Warning: Generated {len(variations)} (Expected 8-10)")

    print("\n=== SCENARIO 2: MISSING SIIS TEXT (Fast-Fail Path) ===")
    plan_empty = await extract_troubleshooting_steps(query, siis_response=None)

    # 4. Test Fallback Handling
    if not plan_empty.get("contexts") and plan_empty.get("fallback") == "no_match":
        print("✅ Fallback Logic: PASS (Correctly bypassed extraction and returned 'no_match')")
    else:
        print("❌ Fallback Logic: FAIL (Did not return empty contexts or 'no_match')")

if __name__ == "__main__":
    asyncio.run(run_final_tests())