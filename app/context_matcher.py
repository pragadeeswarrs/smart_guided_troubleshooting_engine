"""High-accuracy hybrid context matcher for SIIS reference knowledge base."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.retrieval import RetrievalEngine

TOPIC_KEYWORDS: Dict[int, List[str]] = {
    1: ["black screen", "screen black", "won't turn on", "blank screen", "screen dead", "display black"],
    2: ["battery", "drain", "draining", "power saving", "dying", "battery life", "battery usage"],
    3: ["wifi", "wi-fi", "router", "network disconnect", "dropping connection", "internet drop", "wifi drops"],
    4: ["bluetooth", "headphones", "earbuds", "earphones", "buds", "pair", "cutting out", "unpair"],
    5: ["camera", "photo mode", "camera crash", "crashing", "camera app"],
    6: ["overheat", "overheating", "warm", "hot", "temperature", "charging heat"],
    7: ["touch screen", "touchscreen", "unresponsive", "taps", "registering taps", "touch sensitivity"],
    8: ["sound", "speaker", "audio", "volume", "no sound", "silent speaker"],
    9: ["boot loop", "bootloop", "restarting", "restart loop", "continuous restart", "restarts"],
    10: ["mobile data", "data not working", "no internet icon", "apn", "cellular data"],
    11: ["fingerprint", "biometric", "scanner not recognizing", "finger print"],
    12: ["microphone", "mic", "voice recording", "calls audio", "mic not working"],
    13: ["storage", "running out of space", "storage full", "space breakdown", "clean storage", "out of space"],
    14: ["gps", "location", "navigation lost", "inaccurate location", "maps lost"],
    15: ["notification", "delayed alert", "notifications not showing", "delayed notifications"],
    16: ["wireless charging", "charging pad", "wireless charger"],
    17: ["flickering", "green tint", "screen flicker", "green screen", "display tint"],
    18: ["sim card", "no sim", "eject sim", "sim not detected", "sim error"],
    19: ["play store", "google play", "downloading apps", "play store stuck"],
    20: ["freezing", "lagging", "slow", "phone is freezing", "apps lagging", "lag"]
}


class SIISContextMatcher:
    def __init__(self, data_path: str = "data/siis_responses.json"):
        self.scenarios = self._load_scenarios(data_path)
        self.retrieval_engine = RetrievalEngine()
        self.model = self.retrieval_engine.model
        
        # Precompute scenario embeddings for fast semantic match
        if self.scenarios and self.model:
            scenario_texts = [f"{s.get('query', '')} {str(s.get('siis_response', ''))[:140]}" for s in self.scenarios]
            self.scenario_embeddings = self.model.encode(scenario_texts, convert_to_tensor=True)
        else:
            self.scenario_embeddings = None

    def _load_scenarios(self, data_path: str) -> List[Dict[str, Any]]:
        candidate_paths = [
            data_path,
            "data/siis_responses.json",
            "siis_responses.json",
            os.path.join(os.path.dirname(__file__), "..", "data", "siis_responses.json"),
            os.path.join(os.path.dirname(__file__), "..", "siis_responses.json"),
        ]
        for p in candidate_paths:
            if p and os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data if isinstance(data, list) else data.get("responses", [])
                except Exception:
                    pass
        return []

    def match_siis_context(self, query: str) -> Optional[str]:
        """Hybrid matcher returning the SIIS response text for any natural query."""
        if not self.scenarios:
            return None

        q_lower = query.strip().lower()
        if not q_lower:
            return None

        # 1. Exact match fast-path
        for s in self.scenarios:
            sq = s.get("query", "").strip().lower()
            if q_lower == sq:
                siis_val = s.get("siis_response", "")
                return siis_val.get("content", str(siis_val)) if isinstance(siis_val, dict) else str(siis_val)

        # 2. Topic keyword score boost
        keyword_boosts = [0.0] * len(self.scenarios)
        for sc_idx, s in enumerate(self.scenarios):
            sc_id = s.get("scenario_id", sc_idx + 1)
            keywords = TOPIC_KEYWORDS.get(sc_id, [])
            for kw in keywords:
                if kw in q_lower:
                    keyword_boosts[sc_idx] += 0.48
                else:
                    words = kw.split()
                    if len(words) > 1 and all(w in q_lower for w in words):
                        keyword_boosts[sc_idx] += 0.40

        # 3. Vector semantic similarity using all-MiniLM-L6-v2
        scored: List[Tuple[float, int, float]] = []

        if self.scenario_embeddings is not None and self.model:
            from sentence_transformers import util
            q_emb = self.model.encode(query, convert_to_tensor=True)
            hits = util.semantic_search(q_emb, self.scenario_embeddings, top_k=len(self.scenarios))[0]
            for h in hits:
                idx = h["corpus_id"]
                score = h["score"] + keyword_boosts[idx]
                if score >= 0.42:
                    scored.append((score, idx, keyword_boosts[idx]))

            scored.sort(key=lambda x: x[0], reverse=True)

        # Fallback to keyword boost alone if model was unavailable
        if not scored:
            max_boost = max(keyword_boosts)
            if max_boost > 0.35:
                best_idx = keyword_boosts.index(max_boost)
                scored.append((max_boost, best_idx, max_boost))

        # Check if we have any confident match
        if not scored:
            max_raw = max(keyword_boosts) if keyword_boosts else 0.0
            print(f"[DEBUG] No confident SIIS match for: \"{query}\" (Best score: {max_raw:.3f})")
            return None

        best_score, best_idx, _ = scored[0]
        selected_indices = [best_idx]

        # Multi-intent / composite query detection:
        # If query describes multiple distinct issues (e.g. "storage full and wireless charging not working")
        if len(scored) > 1:
            for score, idx, kw_boost in scored[1:3]:
                if (kw_boost >= 0.40 and score >= 0.65) or (score >= 0.90):
                    if idx not in selected_indices:
                        selected_indices.append(idx)

        # Extract and concatenate SIIS context texts
        texts = []
        matched_labels = []
        for idx in selected_indices:
            s = self.scenarios[idx]
            siis_val = s.get("siis_response", "")
            text = siis_val.get("content", str(siis_val)) if isinstance(siis_val, dict) else str(siis_val)
            if text.strip():
                texts.append(text.strip())
                matched_labels.append(f"[Scenario {s.get('scenario_id')}] \"{s.get('query')}\"")

        print(f"[DEBUG] Semantic Match: \"{query}\" -> {' & '.join(matched_labels)} (Top score: {best_score:.3f})")
        return "\n\n".join(texts)


# Global singleton instance
context_matcher = SIISContextMatcher()

def find_siis_context(query: str) -> Optional[str]:
    return context_matcher.match_siis_context(query)
