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
            return json.load(f)

    def _build_index(self):
        if not self.catalog:
            return

        corpus_texts = []
        
        for idx, item in enumerate(self.catalog):
            # Rule 1: Index metadata fields ONLY. NEVER include the URI string itself.
            description = item.get("description", "")
            message = item.get("message", "")
            qna_desc = item.get("qna_description", "")
            original_type = item.get("originalType", "")

            searchable_text = f"{description} {message} {qna_desc} {original_type}".strip()
            if not searchable_text:
                searchable_text = "setting"

            corpus_texts.append(searchable_text)
            
            # Store in ChromaDB
            embeddings = self.model.encode(searchable_text).tolist()
            self.collection.add(
                documents=[searchable_text],
                embeddings=[embeddings],
                metadatas=[{"catalog_idx": idx}],
                ids=[str(idx)]
            )

        # Initialize BM25 index
        tokenized_corpus = [text.lower().split() for text in corpus_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search_deeplink(self, query: str) -> dict[str, Any]:
        if not self.catalog:
            return {"deeplink_uri": None, "category": "manual", "validation": None}

        # Vector search via ChromaDB
        query_embedding = self.model.encode(query).tolist()
        vector_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        
        # BM25 Keyword Search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query) if self.bm25 else []

        best_idx = 0
        if vector_results and vector_results.get("metadatas") and vector_results["metadatas"][0]:
            best_idx = vector_results["metadatas"][0][0]["catalog_idx"]
        elif bm25_scores:
            best_idx = int(max(range(len(bm25_scores)), key=lambda i: bm25_scores[i]))

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
