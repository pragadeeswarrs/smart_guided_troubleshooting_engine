import json
import os
import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

class RetrievalEngine:
    def __init__(self, data_path=os.path.join("data", "deeplinks.json")):
        self.data_path = data_path
        self.documents, self.metadatas, self.ids = self._parse_deeplinks()
        
        # 1. Load Embedding Model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # 2. Setup Vector Store
        embeddings = self.model.encode(self.documents).tolist()
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Reset collection on startup to prevent duplication
        if "samsung_deeplinks" in [c.name for c in self.client.list_collections()]:
            self.client.delete_collection("samsung_deeplinks")
            
        self.collection = self.client.create_collection(name="samsung_deeplinks")
        self.collection.add(
            ids=self.ids,
            embeddings=embeddings,
            documents=self.documents,
            metadatas=self.metadatas
        )

        # 3. Setup BM25 Keyword Search
        tokenized_corpus = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _parse_deeplinks(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Cannot find {self.data_path}")

        with open(self.data_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        if isinstance(catalog, dict):
            catalog = catalog.get("deeplinks", list(catalog.values()))

        documents, metadatas, ids = [], [], []
        for idx, item in enumerate(catalog):
            if not isinstance(item, dict):
                continue

            text = f"{item.get('description', '')} {item.get('message', '')} {item.get('qna_description', '')}".strip()
            meta = {
                "uri": item.get("deeplink", "None"),
                "category": item.get("category", "auto")
            }
            documents.append(text)
            metadatas.append(meta)
            ids.append(str(idx))

        return documents, metadatas, ids

    def search_deeplink(self, query: str) -> dict:
        """Dense + BM25 + Reciprocal Rank Fusion Search"""
        # Dense Search
        query_emb = self.model.encode([query]).tolist()
        vector_res = self.collection.query(query_embeddings=query_emb, n_results=10)
        vector_ids = vector_res['ids'][0]

        # BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:10]
        bm25_ids = [str(i) for i in bm25_top_indices]

        # Reciprocal Rank Fusion
        rrf_scores = {}
        for rank, doc_id in enumerate(vector_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60 + rank))
        for rank, doc_id in enumerate(bm25_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60 + rank))

        best_id = int(sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[0])

        return {
            "matched_text": self.documents[best_id],
            "deeplink_uri": self.metadatas[best_id]["uri"],
            "category": self.metadatas[best_id]["category"]
        }

    @staticmethod
    def sort_actions_by_category(actions: list) -> list:
        """Sorts actions: auto first, manual second, critical last"""
        order = {"auto": 0, "manual": 1, "critical": 2}
        return sorted(actions, key=lambda x: order.get(x.get("category", "manual"), 1))

# Local test
if __name__ == "__main__":
    engine = RetrievalEngine()
    result = engine.search_deeplink("Screen brightness keeps flickering")
    print("\n✅ Engine operational!")
    print(f"Matched Deeplink: {result['deeplink_uri']}")