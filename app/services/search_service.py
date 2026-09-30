"""Deeplink retrieval and action categorization service."""
from __future__ import annotations

from typing import Any
from app.retrieval import RetrievalEngine

# Initialize retrieval engine instance
retrieval_engine = RetrievalEngine(data_path="data/deeplinks.json")


def _classify_category(action_name: str, desc: str, steps_text: str, current_cat: str) -> str:
    """Smart classification of action category (auto, manual, critical)."""
    text = f"{action_name} {desc} {steps_text}".lower()

    critical_keywords = [
        "factory reset", "wipe cache", "reset network", "recovery menu",
        "hard reset", "factory data reset", "reformat"
    ]
    if any(k in text for k in critical_keywords):
        return "critical"

    # Keywords strongly indicating software / UI settings navigation (auto-executable via Bixby / settings)
    auto_keywords = [
        "settings", "tap", "open", "toggle", "enable", "disable",
        "turn on", "turn off", "configure", "slider", "optimize",
        "clear cache", "clear data", "battery", "display", "wi-fi", "wifi",
        "bluetooth", "airplane", "storage", "sound", "volume", "notification"
    ]

    # Explicit hardware-only inspection keywords
    hardware_only_keywords = [
        "micro-fiber", "microfiber", "clean", "lint", "pinhole", "soft brush",
        "protective case", "drop", "crack", "water", "cable", "charger pad",
        "router", "physical"
    ]

    if current_cat == "auto":
        return "auto"

    if any(k in text for k in auto_keywords):
        # If it also contains hardware words, check if it explicitly mentions navigating settings
        if "settings" in text or "open " in text or "tap " in text or "toggle" in text:
            return "auto"

    if any(k in text for k in hardware_only_keywords):
        return "manual"

    if current_cat in ["auto", "manual", "critical"]:
        return current_cat

    return "auto" if any(k in text for k in auto_keywords) else "manual"


async def map_deeplinks(steps: dict[str, Any]) -> dict[str, Any]:
    """Attach actionableDeeplink and validationDeeplink to each step."""
    if not isinstance(steps, dict):
        return steps

    contexts = steps.get("contexts", [])
    if not isinstance(contexts, list):
        return steps

    for ctx in contexts:
        if not isinstance(ctx, dict):
            continue

        raw_actions = ctx.get("actions", [])
        if not isinstance(raw_actions, list):
            continue

        actions = [a for a in raw_actions if isinstance(a, dict)]
        has_auto = any(str(a.get("category", "")).lower() == "auto" for a in actions)

        for idx, action in enumerate(actions):

            action_name = str(action.get("actionName", "")).strip()
            desc = str(action.get("description", "")).strip()
            step_groups = action.get("stepGroups", [])

            all_steps = []
            for g in step_groups:
                if isinstance(g, dict) and "steps" in g:
                    all_steps.extend([str(s) for s in g["steps"]])
            steps_text = " ".join(all_steps)

            raw_cat = str(action.get("category", "")).lower().strip()
            category = _classify_category(action_name, desc, steps_text, raw_cat)

            # If no action was auto yet and this is the first settings action, ensure it's auto
            if not has_auto and idx == 0 and category != "critical":
                category = "auto"
                has_auto = True

            action["category"] = category

            # Query ChromaDB + BM25 hybrid search engine for catalog match
            search_query = f"{action_name} {desc} {steps_text[:120]}".strip()
            match = retrieval_engine.search_deeplink(search_query) or {}

            matched_uri = match.get("deeplink") or match.get("deeplink_uri")
            validation_obj = match.get("validation")

            for group in step_groups:
                if not isinstance(group, dict):
                    continue

                if category == "auto":
                    if matched_uri:
                        group["actionableDeeplink"] = {
                            "deeplink": matched_uri,
                            "description": match.get("description", "It will open settings screen"),
                            "message": match.get("message", f"{action_name} Settings"),
                        }
                    else:
                        # Fallback dummy positive deeplink for auto action
                        group["actionableDeeplink"] = {
                            "deeplink": "bixby://dummy_positive",
                            "description": "It will open device settings screen",
                            "message": f"{action_name} Settings" if action_name else "Device Settings",
                        }

                    if validation_obj:
                        group["validationDeeplink"] = validation_obj
                    else:
                        group["validationDeeplink"] = None

                elif category == "critical" and matched_uri:
                    group["actionableDeeplink"] = {
                        "deeplink": matched_uri,
                        "description": match.get("description", "It will open reset screen"),
                        "message": match.get("message", f"{action_name} Settings"),
                    }
                    group["validationDeeplink"] = None
                else:
                    # Manual action: no required deeplink
                    group["actionableDeeplink"] = None
                    group["validationDeeplink"] = None

        # Sort actions by priority: auto -> manual -> critical (Block A2)
        category_order = {"auto": 0, "manual": 1, "critical": 2}
        actions.sort(key=lambda a: category_order.get(a.get("category", "manual"), 1))
        ctx["actions"] = actions

    return steps
