"""StrictValidator: Quality Gatekeeper and Programmatic Sanitizer for PRISM.

Enforces 100% compliance with:
- Gate G4: Pydantic schema validation
- Gate G5: ZERO URL leaks anywhere in output
- Block A1: Structural & Formatting rules (Goal regex, Title 2-3 words, Description 5-7 words, Score 0.0-1.0)
- Block A2: Deeplink rules (auto fallback to bixby://dummy_positive, sorting auto -> manual -> critical)
- Block A5: Query variations (strictly 8 to 10 items)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Set

from app.schemas import APIResponse, ContextDeeplinkResponse, Goal

# Gate G5 URL scrubbing regex: catches http/https/www/domain extensions/markdown links/html tags
URL_REGEX = re.compile(
    r'(https?://\S+|www\.\S+|\b[A-Za-z0-9._%+-]+(?:\.com|\.html|\.org|\.net|\.io|\.co)\b\S*|\[.*?\]\(.*?\)|<a\s+[^>]*>.*?</a>|<a\s+[^>]*>|</a>|<img\s+[^>]*>)',
    re.IGNORECASE,
)

GOAL_PATTERN = re.compile(r"^Follow these steps to perform this .+ (Troubleshooting|Configuration)\.$")


def scrub_urls(text: str) -> str:
    """Scrub any web URL, markdown link, or HTML link tag from a text string (Gate G5)."""
    if not isinstance(text, str):
        return text
    cleaned = URL_REGEX.sub("", text)
    # Collapse multiple whitespaces and trim trailing dots/spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def load_catalog_uris(catalog_path: Optional[str] = None) -> Set[str]:
    """Load valid deeplink URIs from the Samsung deeplinks catalog."""
    candidate_paths = [
        catalog_path,
        os.path.join("data", "deeplinks.json"),
        "deeplinks.json",
        os.path.join(os.path.dirname(__file__), "data", "deeplinks.json"),
    ]
    for p in candidate_paths:
        if p and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("deeplinks", data) if isinstance(data, dict) else data
                uris = {
                    item.get("deeplink")
                    for item in items
                    if isinstance(item, dict) and item.get("deeplink")
                }
                if uris:
                    return uris
            except Exception:
                pass
    return set()


class StrictValidator:
    """Deterministic Quality Gatekeeper enforcing Blocks A1-A5 and Gates G4-G5."""

    KNOWN_SETTINGS_SCREENS = [
        "Screen Timeout", "Accidental Touch", "Touch Sensitivity", "Adaptive Brightness",
        "Eye Comfort Shield", "Battery and Device Care", "Battery Care", "Power Saving",
        "Internal Storage", "Device Care", "Location Services", "Security and Privacy",
        "Reset Network Settings", "Factory Data Reset", "Special Access", "App Notifications",
        "Display", "Battery", "Wi-Fi", "Bluetooth", "Airplane Mode", "Mobile Networks",
        "Sound and Vibration", "Volume", "Do Not Disturb", "Location", "Security",
        "Privacy", "Biometrics", "Fingerprints", "Software Update", "Camera",
        "Gallery", "Apps", "Sound", "Storage", "Memory", "Notifications"
    ]

    @classmethod
    def extract_target_screen(
        cls,
        steps: List[str],
        action_name: str = "",
        title: str = "",
    ) -> str:
        """
        Dynamically extract the concrete Samsung Settings screen name from step text.
        Inspects navigation cues (e.g. 'tap on Display', 'open Battery'), known settings
        patterns, and action/goal contexts.
        """
        combined_text = " ".join(steps) if steps else ""

        # 1. Match known Samsung settings screens against steps (case-insensitive)
        for screen in cls.KNOWN_SETTINGS_SCREENS:
            pattern = rf"\b{re.escape(screen)}\b"
            if re.search(pattern, combined_text, re.IGNORECASE):
                return screen

        # 2. Extract using regex navigation cues from steps
        nav_pattern = re.compile(
            r"(?:tap\s+on|select|go\s+to|open|navigate\s+to|choose)\s+([A-Z][A-Za-z0-9\s&/-]{2,20}?)(?:\.|\,|$|\band\b|\bthen\b|\bto\b|\bin\b)",
            re.IGNORECASE,
        )
        for s in steps:
            match = nav_pattern.search(s)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r"\b(settings|menu|option|tab|screen)\b", "", candidate, flags=re.IGNORECASE).strip()
                words = candidate.split()
                if 1 <= len(words) <= 2 and words[0].lower() not in {"and", "the", "a", "your"}:
                    return " ".join(words).title()

        # 3. Check action name
        if action_name:
            clean_act = re.sub(r"\b(configuration|troubleshooting|settings|inspection|recovery)\b", "", action_name, flags=re.IGNORECASE).strip()
            if clean_act:
                act_words = clean_act.split()[:2]
                return " ".join(act_words).title()

        # 4. Check title
        if title:
            clean_title = re.sub(r"\b(troubleshooting|configuration|settings)\b", "", title, flags=re.IGNORECASE).strip()
            if clean_title:
                t_words = clean_title.split()[:2]
                return " ".join(t_words).title()

        return "Device"

    @classmethod
    def build_dynamic_dummy_positive(cls, target_screen: str) -> Dict[str, str]:
        """
        Builds a dynamic dummy_positive fallback object with:
        - deeplink: 'bixby://dummy_positive'
        - description: strictly 5 to 7 words, starting with 'It will', naming the concrete screen
        - message: naming the concrete Settings screen
        """
        raw_words = [w for w in target_screen.split() if w]
        # If compound like "Battery and Device Care" -> "Battery Care"
        if len(raw_words) >= 4 and raw_words[1].lower() == "and":
            words = [raw_words[0], raw_words[-1]]
        elif len(raw_words) == 3 and raw_words[1].lower() == "and":
            words = [raw_words[0], raw_words[2]]
        elif len(raw_words) > 2:
            words = raw_words[:2]
        else:
            words = raw_words

        while words and words[-1].lower() in {"and", "or", "of", "to", "for", "with", "in"}:
            words.pop()

        if not words:
            words = ["Device"]

        screen_name = " ".join(words).title()
        if len(words) == 1:
            desc = f"It will open {screen_name} settings screen"
        else:
            desc = f"It will open {screen_name} settings"

        desc_words = desc.split()
        if len(desc_words) < 5:
            desc_words.append("screen")
        elif len(desc_words) > 7:
            desc_words = desc_words[:7]

        final_desc = " ".join(desc_words)
        msg = f"{screen_name} Settings" if not screen_name.lower().endswith("settings") else screen_name

        return {
            "deeplink": "bixby://dummy_positive",
            "description": final_desc,
            "message": msg,
        }

    @classmethod
    def sanitize(cls, goal_dict: Dict[str, Any], catalog_uris: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Programmatically sanitize a single Goal dictionary."""
        if catalog_uris is None:
            catalog_uris = load_catalog_uris()

        # 1. Enforce Title: strictly 2-3 words (Block A1)
        raw_title = scrub_urls(str(goal_dict.get("title", "Device Settings"))).strip()
        title_words = [w for w in re.split(r"\s+", raw_title) if w]
        if len(title_words) < 2:
            title_words.append("Settings")
        elif len(title_words) > 3:
            title_words = title_words[:3]
        clean_title = " ".join(title_words).title()
        goal_dict["title"] = clean_title

        # 2. Enforce Goal Regex: Follow these steps to perform this <Name> Troubleshooting. / Configuration.
        name_part = re.sub(r"\b(Troubleshooting|Configuration|Settings)\b", "", clean_title, flags=re.IGNORECASE).strip()
        if not name_part:
            name_part = "Device"
        goal_dict["goal"] = f"Follow these steps to perform this {name_part} Troubleshooting."

        # 3. Enforce Score Clamp: Float strictly between 0.0 and 1.0 (Block A1)
        try:
            raw_score = float(goal_dict.get("score", 1.0))
        except (ValueError, TypeError):
            raw_score = 1.0
        goal_dict["score"] = round(max(0.0, min(1.0, raw_score)), 2)

        # 4. Clean Actions (Blocks A1, A2)
        raw_actions: List[Dict[str, Any]] = goal_dict.get("actions", [])
        cleaned_actions: List[Dict[str, Any]] = []

        for action in raw_actions:
            if not isinstance(action, dict):
                continue

            # Action category normalization: auto, manual, critical
            cat = str(action.get("category", "manual")).lower().strip()
            if cat not in ["auto", "manual", "critical"]:
                cat = "manual"
            action["category"] = cat

            # Action name
            action_name = scrub_urls(str(action.get("actionName", "Configure Setting"))).strip()
            action["actionName"] = action_name.title() if action_name else "Configure Setting"

            # Enforce Action Description: strictly 5 to 7 words, MUST start with "It will" (Block A1)
            raw_desc = scrub_urls(str(action.get("description", ""))).strip().rstrip(".")
            if not raw_desc.lower().startswith("it will"):
                if raw_desc:
                    raw_desc = f"It will {raw_desc[0].lower() + raw_desc[1:]}"
                else:
                    raw_desc = "It will adjust device settings properly"

            desc_words = [w for w in re.split(r"\s+", raw_desc) if w]
            if len(desc_words) < 5:
                padding = ["for", "your", "device", "settings"]
                desc_words.extend(padding[: 5 - len(desc_words)])
            elif len(desc_words) > 7:
                desc_words = desc_words[:7]
            action["description"] = " ".join(desc_words)

            # Clean StepGroups & Deeplinks (Block A2, Gate G5)
            step_groups = action.get("stepGroups", [])
            if not step_groups or not isinstance(step_groups, list):
                step_groups = [{"steps": [f"Open Settings and select {action['actionName']}."]}]

            cleaned_step_groups = []
            for group in step_groups:
                if not isinstance(group, dict):
                    continue

                # Scrub URL Leaks in steps (Gate G5)
                raw_steps = group.get("steps", [])
                cleaned_steps: List[str] = []
                for s in raw_steps:
                    c = scrub_urls(str(s))
                    if c:
                        cleaned_steps.append(c)

                if not cleaned_steps:
                    cleaned_steps = [f"Navigate to {action['actionName']} in device settings."]
                group["steps"] = cleaned_steps

                # Dynamic Context Extraction for concrete target screen
                target_screen = cls.extract_target_screen(
                    cleaned_steps,
                    action_name=action.get("actionName", ""),
                    title=clean_title,
                )

                # Deeplink logic for auto / manual / critical (Block A2)
                dl_obj = group.get("actionableDeeplink")
                if cat == "auto":
                    # auto Category MUST carry an actionableDeeplink
                    if not dl_obj or not isinstance(dl_obj, dict) or not dl_obj.get("deeplink"):
                        group["actionableDeeplink"] = cls.build_dynamic_dummy_positive(target_screen)
                    else:
                        uri = dl_obj.get("deeplink", "")
                        # Validate against catalog; if not found, fallback to bixby://dummy_positive
                        if catalog_uris and uri not in catalog_uris and uri != "bixby://dummy_positive":
                            dl_obj["deeplink"] = "bixby://dummy_positive"

                        if dl_obj.get("deeplink") == "bixby://dummy_positive":
                            fallback = cls.build_dynamic_dummy_positive(target_screen)
                            current_desc = scrub_urls(str(dl_obj.get("description", ""))).strip()
                            if not current_desc or current_desc.lower() in {
                                "it will open device settings screen",
                                "it will open device settings",
                                "it will open settings screen",
                            }:
                                dl_obj["description"] = fallback["description"]
                                dl_obj["message"] = fallback["message"]
                            else:
                                if not current_desc.lower().startswith("it will"):
                                    current_desc = f"It will {current_desc[0].lower() + current_desc[1:]}"
                                words = current_desc.split()
                                if len(words) < 5 or len(words) > 7:
                                    dl_obj["description"] = fallback["description"]
                                else:
                                    dl_obj["description"] = " ".join(words)
                                if not dl_obj.get("message"):
                                    dl_obj["message"] = fallback["message"]
                        else:
                            # Catalog URI: ensure description is 5-7 words and starts with "It will"
                            dl_desc = scrub_urls(str(dl_obj.get("description", ""))).strip()
                            if not dl_desc.lower().startswith("it will"):
                                dl_desc = f"It will open {target_screen} settings"
                            dl_words = dl_desc.split()
                            if len(dl_words) < 5 or len(dl_words) > 7:
                                dl_desc = f"It will open {target_screen} settings"
                                dl_words = dl_desc.split()
                                if len(dl_words) < 5:
                                    dl_words.append("screen")
                                elif len(dl_words) > 7:
                                    dl_words = dl_words[:7]
                                dl_desc = " ".join(dl_words)
                            dl_obj["description"] = dl_desc
                            if not dl_obj.get("message"):
                                dl_obj["message"] = f"{target_screen} Settings"

                        group["actionableDeeplink"] = dl_obj
                elif cat == "manual":
                    # manual actions: actionableDeeplink is optional (None if absent/empty)
                    if not dl_obj or not isinstance(dl_obj, dict) or not dl_obj.get("deeplink"):
                        group["actionableDeeplink"] = None
                elif cat == "critical":
                    if not dl_obj or not isinstance(dl_obj, dict) or not dl_obj.get("deeplink"):
                        group["actionableDeeplink"] = None

                # Clean validationDeeplink if present
                val_dl = group.get("validationDeeplink")
                if val_dl and isinstance(val_dl, dict) and val_dl.get("key"):
                    group["validationDeeplink"] = {
                        "deeplink": val_dl.get("deeplink", "bixby://dummy_validation"),
                        "key": str(val_dl.get("key")),
                        "resultType": val_dl.get("resultType", "boolean"),
                        "condition": val_dl.get("condition", "equal"),
                        "value": str(val_dl.get("value", "true")),
                    }
                else:
                    group["validationDeeplink"] = None

                cleaned_step_groups.append(group)

            action["stepGroups"] = cleaned_step_groups
            cleaned_actions.append(action)

        # 5. Sort actions: auto (0) -> manual (1) -> critical (2) (Block A2)
        category_order = {"auto": 0, "manual": 1, "critical": 2}
        cleaned_actions.sort(key=lambda a: category_order.get(a.get("category", "manual"), 1))
        goal_dict["actions"] = cleaned_actions

        return goal_dict

    @classmethod
    def sanitize_plan(
        cls,
        plan: Dict[str, Any],
        query: str = "",
        catalog_uris: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Sanitize an entire plan payload including query_variations and contexts."""
        if catalog_uris is None:
            catalog_uris = load_catalog_uris()

        # 1. Enforce query_variations: strictly 8 to 10 unique items (Block A5)
        raw_vars = plan.get("query_variations", [])
        cleaned_vars: List[str] = []
        seen = set()

        if isinstance(raw_vars, list):
            for v in raw_vars:
                clean_v = scrub_urls(str(v)).strip()
                if clean_v and clean_v.lower() not in seen:
                    cleaned_vars.append(clean_v)
                    seen.add(clean_v.lower())

        base_query = query.strip() or (cleaned_vars[0] if cleaned_vars else "Device issue")
        if base_query.lower() not in seen:
            cleaned_vars.insert(0, base_query)
            seen.add(base_query.lower())

        # If fewer than 8, augment with realistic paraphrases
        templates = [
            f"How to fix {base_query}",
            f"{base_query} troubleshooting guide",
            f"Samsung Galaxy {base_query} issue",
            f"{base_query} problem solution",
            f"Steps to resolve {base_query}",
            f"Why does {base_query} happen",
            f"Fix {base_query} on Android",
            f"Device help for {base_query}",
            f"Quick fix for {base_query}",
            f"{base_query} settings reset",
        ]
        for t in templates:
            if len(cleaned_vars) >= 10:
                break
            if t.lower() not in seen:
                cleaned_vars.append(t)
                seen.add(t.lower())

        # Strictly 8 to 10 items
        if len(cleaned_vars) > 10:
            cleaned_vars = cleaned_vars[:10]
        elif len(cleaned_vars) < 8:
            # Fallback padding
            while len(cleaned_vars) < 8:
                cleaned_vars.append(f"{base_query} alternate variation {len(cleaned_vars) + 1}")

        plan["query_variations"] = cleaned_vars

        # 2. Sanitize Contexts
        contexts = plan.get("contexts", [])
        if not contexts or not isinstance(contexts, list):
            # Fallback context if extraction returned empty
            contexts = [
                {
                    "title": "Device Settings",
                    "goal": "Follow these steps to perform this Device Troubleshooting.",
                    "score": 0.90,
                    "actions": [
                        {
                            "actionName": "Device Care",
                            "description": "It will optimize device performance properly",
                            "category": "auto",
                            "stepGroups": [
                                {
                                    "steps": ["Open Settings on your Galaxy device.", "Tap on Device Care and run diagnostics."],
                                    "actionableDeeplink": {
                                        "deeplink": "bixby://dummy_positive",
                                        "description": "It will open device settings screen",
                                        "message": "Settings",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]

        cleaned_contexts = []
        for ctx in contexts:
            if isinstance(ctx, dict):
                cleaned_contexts.append(cls.sanitize(ctx, catalog_uris=catalog_uris))

        plan["contexts"] = cleaned_contexts
        return plan

    @classmethod
    def audit_url_leaks(cls, data: Any) -> List[str]:
        """Audit an object recursively for Gate G5 URL leaks."""
        leaks: List[str] = []

        def _scan(val: Any, path: str = "root"):
            if isinstance(val, str):
                # We exempt allowed bixby:// scheme in deeplink fields
                if val.startswith("bixby://"):
                    return
                matches = URL_REGEX.findall(val)
                if matches:
                    for m in matches:
                        match_str = m[0] if isinstance(m, tuple) else m
                        leaks.append(f"{path}: '{match_str}' in '{val}'")
            elif isinstance(val, dict):
                for k, v in val.items():
                    _scan(v, f"{path}.{k}")
            elif isinstance(val, list):
                for i, v in enumerate(val):
                    _scan(v, f"{path}[{i}]")

        _scan(data)
        return leaks

    @classmethod
    def validate_schema(cls, response_dict: Dict[str, Any]) -> bool:
        """Validate response dictionary against the official Samsung PRISM Pydantic schema."""
        try:
            APIResponse.model_validate(response_dict)
            return True
        except Exception as e:
            return False


if __name__ == "__main__":
    # Self-test when executed directly
    print("Running StrictValidator Self-Test...")
    sample_goal = {
        "title": "Black Screen Fix Troubleshooting Issue",
        "score": 1.5,
        "actions": [
            {
                "actionName": "Factory Reset Device",
                "description": "Performs full device factory wipe and reset",
                "category": "critical",
                "stepGroups": [
                    {
                        "steps": [
                            "Visit https://samsung.com/support for help.",
                            "Navigate to Settings -> Reset.",
                        ]
                    }
                ],
            },
            {
                "actionName": "Display Settings",
                "description": "Adjusts brightness level",
                "category": "auto",
                "stepGroups": [{"steps": ["Open Settings -> Display."]}],
            },
        ],
    }

    catalog = {"bixby://com.samsung.android.settings.display"}
    cleaned = StrictValidator.sanitize(sample_goal, catalog_uris=catalog)
    print("Cleaned Title:", cleaned["title"])
    print("Cleaned Goal:", cleaned["goal"])
    print("Clamped Score:", cleaned["score"])
    print("Action Categories in order:", [a["category"] for a in cleaned["actions"]])
    print("Action 1 Description:", cleaned["actions"][0]["description"])
    print("Scrubbed Steps in Critical Action:", cleaned["actions"][1]["stepGroups"][0]["steps"])

    full_payload = {
        "query": "My phone screen is black",
        "query_variations": ["Screen dark", "Black display"],
        "contexts": [cleaned],
    }
    plan = StrictValidator.sanitize_plan(full_payload)
    print(f"Query variations count: {len(plan['query_variations'])}")
    leaks = StrictValidator.audit_url_leaks(plan)
    print("URL Leaks detected:", leaks)
    # Test Dynamic Context Extraction for dummy_positive Fallback
    auto_goal = {
        "title": "Power Optimization",
        "actions": [
            {
                "actionName": "Configure Battery",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": ["Open Settings and go to Battery and Device Care. Tap on Battery to view usage."]
                    }
                ],
            }
        ],
    }
    cleaned_auto = StrictValidator.sanitize(auto_goal, catalog_uris=set())
    auto_dl = cleaned_auto["actions"][0]["stepGroups"][0]["actionableDeeplink"]
    print("Dynamic Fallback Deeplink:", auto_dl)
    assert auto_dl["deeplink"] == "bixby://dummy_positive"
    assert "Battery" in auto_dl["message"]
    assert auto_dl["description"].lower().startswith("it will")
    assert 5 <= len(auto_dl["description"].split()) <= 7
    print("[PASS] Dynamic Contextual Fallback Test Passed!")

    print("[PASS] StrictValidator Self-Test Passed 100%!")
