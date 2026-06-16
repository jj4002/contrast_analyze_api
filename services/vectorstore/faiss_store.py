import os
import pickle
import threading

import faiss
import numpy as np

from config import VECTOR_STORE_DIR, logger
from services.vectorstore.document import Document
from services.vectorstore.embeddings import embed_texts, get_embedding_dim


class FaissStore:
    """Minimal FAISS-backed vector store with metadata filtering, persisted to disk."""

    def __init__(self, name: str):
        self.name = name
        self.index_path = os.path.join(VECTOR_STORE_DIR, f"{name}.index")
        self.meta_path = os.path.join(VECTOR_STORE_DIR, f"{name}.pkl")
        self.texts: list[str] = []
        self.metadatas: list[dict] = []
        self._lock = threading.Lock()
        self.index = self._load()

    def _load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "rb") as f:
                    self.texts, self.metadatas = pickle.load(f)
                return faiss.read_index(self.index_path)
            except Exception as e:
                logger.error(f"Failed to load FAISS store '{self.name}': {e}, starting fresh")
        return faiss.IndexFlatIP(get_embedding_dim())

    def save(self):
        with self._lock:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "wb") as f:
                pickle.dump((self.texts, self.metadatas), f)

    def reset(self):
        """Wipe the collection in memory and on disk (used to rebuild from a source of truth)."""
        with self._lock:
            self.index = faiss.IndexFlatIP(get_embedding_dim())
            self.texts = []
            self.metadatas = []
        self.save()

    def add_documents(self, docs: list[Document], persist: bool = True):
        if not docs:
            return
        vectors = embed_texts([d.page_content for d in docs])
        with self._lock:
            self.index.add(vectors)
            self.texts.extend(d.page_content for d in docs)
            self.metadatas.extend(d.metadata for d in docs)
        if persist:
            self.save()

    def _matching_indices(self, where: dict | None) -> list[int]:
        if not where:
            return list(range(len(self.texts)))
        return [i for i, m in enumerate(self.metadatas) if all(m.get(k) == v for k, v in where.items())]

    def get(self, where: dict | None = None) -> dict:
        idxs = self._matching_indices(where)
        return {
            "documents": [self.texts[i] for i in idxs],
            "metadatas": [self.metadatas[i] for i in idxs],
        }

    def similarity_search(self, query: str, k: int = 5, where: dict | None = None, min_score: float | None = None) -> list[Document]:
        if not self.texts:
            return []
        query_vector = embed_texts([query])

        if where:
            candidates = self._matching_indices(where)
            if not candidates:
                return []
            vectors = np.vstack([self.index.reconstruct(i) for i in candidates])
            scores = vectors @ query_vector[0]
            ranked = np.argsort(scores)[::-1][:k]
            return [
                Document(self.texts[candidates[i]], self.metadatas[candidates[i]])
                for i in ranked
                if min_score is None or scores[i] >= min_score
            ]

        scores, idxs = self.index.search(query_vector, min(k, len(self.texts)))
        return [
            Document(self.texts[i], self.metadatas[i])
            for score, i in zip(scores[0], idxs[0])
            if i != -1 and (min_score is None or score >= min_score)
        ]


_contract_collection = None
_legal_collection = None


def get_contract_collection() -> FaissStore:
    global _contract_collection
    if _contract_collection is None:
        _contract_collection = FaissStore("contracts")
    return _contract_collection


def get_legal_collection() -> FaissStore:
    global _legal_collection
    if _legal_collection is None:
        _legal_collection = FaissStore("legal")
    return _legal_collection
