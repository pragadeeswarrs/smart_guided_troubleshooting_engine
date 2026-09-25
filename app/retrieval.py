"""Hybrid Retrieval Engine using ChromaDB + BM25."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class RetrievalEngine:
    def __init__(self, data_path: str = "data/deeplinks.json"):
        self.data_path = Path(data_path)
        self.catalog = self._load_catalog()
        
        # Initialize embedding model and ChromaDB client
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(name="deeplinks")
        
        self.documents = []
        self.bm25 = None
        
        self._build_index()

    def _load_catalog(self) -> list[dict[str, Any]]:
        if not self.data_path.exists():
            return []
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_items = []
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            # Check for common wrapper keys
            for key in ["deeplinks", "items", "data", "catalog", "entries"]:
                if key in data and isinstance(data[key], list):
                    raw_items = data[key]
                    break
            else:
                # Fallback to dictionary values if mapped by ID
                raw_items = list(data.values())

        # Ensure every item in catalog is strictly a dictionary
        return [item for item in raw_items if isinstance(item, dict)]

    def _build_index(self):
        if not self.catalog:
            return

        corpus_texts = []
        valid_catalog = []
        
        for item in self.catalog:
            # Guard against non-dictionary entries
            if not isinstance(item, dict):
                continue

            # Rule 1: Index metadata fields ONLY. NEVER include the URI string itself.
            description = str(item.get("description", "") or "")
            message = str(item.get("message", "") or "")
            qna_desc = str(item.get("qna_description", "") or "")
            original_type = str(item.get("originalType", "") or "")

            searchable_text = f"{description} {message} {qna_desc} {original_type}".strip()
            if not searchable_text:
                searchable_text = "setting"

            idx = len(valid_catalog)
            corpus_texts.append(searchable_text)
            valid_catalog.append(item)
            
            # Store in ChromaDB
            embeddings = self.model.encode(searchable_text).tolist()
            self.collection.add(
                documents=[searchable_text],
                embeddings=[embeddings],
                metadatas=[{"catalog_idx": idx}],
                ids=[str(idx)]
            )

        self.catalog = valid_catalog

        # Initialize BM25 index
        if corpus_texts:
            tokenized_corpus = [text.lower().split() for text in corpus_texts]
            self.bm25 = BM25Okapi(tokenized_corpus)

    def search_deeplink(self, query: str) -> dict[str, Any]:
        if not self.catalog:
            return {"deeplink_uri": None, "category": "manual", "validation": None}

        # Vector search via ChromaDB
        query_embedding = self.model.encode(query).tolist()
        vector_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["metadatas", "distances"]
        )
        
        best_idx = None
        best_distance = float("inf")

        if vector_results and vector_results.get("metadatas") and vector_results["metadatas"][0]:
            best_idx = vector_results["metadatas"][0][0]["catalog_idx"]
            if vector_results.get("distances") and vector_results["distances"][0]:
                best_distance = vector_results["distances"][0][0]

        # Distance threshold check (> 1.1 means low confidence / no match)
        if best_idx is None or best_distance > 1.1 or best_idx >= len(self.catalog):
            return {"deeplink_uri": None, "category": "manual", "validation": None}

        matched_item = self.catalog[best_idx]

        # Rule 2 & 3: Return verbatim URI, category, and validation object
        return {
            "deeplink_uri": matched_item.get("uri") or matched_item.get("masked_uri"),
            "category": matched_item.get("category", "auto"),
            "validation": matched_item.get("validation")
        }

    def sort_actions_by_category(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority = {"auto": 0, "manual": 1, "critical": 2}
        return sorted(actions, key=lambda x: priority.get(x.get("category", "manual"), 1))
