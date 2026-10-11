from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
import numpy as np
from app.config import settings

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class AbstractVectorStore(ABC):
    """
    Abstract Vector Database interface.
    Allows swappable implementations (FAISS, ChromaDB, Qdrant, Memory).
    """
    @abstractmethod
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> List[int]:
        """Add text chunks and corresponding embedding vectors."""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 4, dataset: str = None) -> List[Tuple[Dict[str, Any], float]]:
        """Search for top_k most similar chunks, returning (chunk_dict, score)."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return total number of vectors in store."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all indexed vectors and metadata."""
        pass

class FAISSVectorStore(AbstractVectorStore):
    """
    FAISS-based vector database using IndexFlatIP (Cosine similarity on normalized vectors).
    """
    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.index = None
        self.metadata_store: List[Dict[str, Any]] = []

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> List[int]:
        if not FAISS_AVAILABLE or self.index is None:
            fallback = MemoryVectorStore(self.dimension)
            return fallback.add_chunks(chunks, embeddings)

        if len(chunks) == 0:
            return []

        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} != index dimension {self.dimension}")

        start_id = len(self.metadata_store)
        self.index.add(embeddings)
        self.metadata_store.extend(chunks)
        return list(range(start_id, len(self.metadata_store)))

    def search(self, query_embedding: np.ndarray, top_k: int = 4, dataset: str = None) -> List[Tuple[Dict[str, Any], float]]:
        if not FAISS_AVAILABLE or self.index is None or self.index.ntotal == 0:
            return []

        # If dataset filtering is requested, we retrieve more candidates then filter
        search_k = min(self.index.ntotal, top_k * 4 if dataset else top_k)
        q = np.ascontiguousarray(query_embedding.reshape(1, -1), dtype=np.float32)
        scores, indices = self.index.search(q, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata_store):
                continue
            meta = self.metadata_store[idx]
            if dataset and meta.get("dataset") != dataset:
                continue
            # Convert inner product to a [0, 1] range similarity
            norm_score = max(0.0, min(1.0, float(score)))
            results.append((meta, norm_score))
            if len(results) >= top_k:
                break

        return results

    def count(self) -> int:
        return self.index.ntotal if (FAISS_AVAILABLE and self.index) else len(self.metadata_store)

    def clear(self) -> None:
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata_store = []

class MemoryVectorStore(AbstractVectorStore):
    """
    Pure NumPy Vector Store fallback with exact cosine similarity.
    """
    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.vectors = np.empty((0, dimension), dtype=np.float32)
        self.metadata_store: List[Dict[str, Any]] = []

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> List[int]:
        if len(chunks) == 0:
            return []
        start_id = len(self.metadata_store)
        if self.vectors.shape[0] == 0:
            self.vectors = embeddings
        else:
            self.vectors = np.vstack([self.vectors, embeddings])
        self.metadata_store.extend(chunks)
        return list(range(start_id, len(self.metadata_store)))

    def search(self, query_embedding: np.ndarray, top_k: int = 4, dataset: str = None) -> List[Tuple[Dict[str, Any], float]]:
        if self.vectors.shape[0] == 0:
            return []

        q = query_embedding.reshape(1, -1)
        sims = np.dot(self.vectors, q.T).flatten()
        sorted_indices = np.argsort(-sims)

        results = []
        for idx in sorted_indices:
            meta = self.metadata_store[idx]
            if dataset and meta.get("dataset") != dataset:
                continue
            score = max(0.0, min(1.0, float(sims[idx])))
            results.append((meta, score))
            if len(results) >= top_k:
                break
        return results

    def count(self) -> int:
        return len(self.metadata_store)

    def clear(self) -> None:
        self.vectors = np.empty((0, self.dimension), dtype=np.float32)
        self.metadata_store = []

# Global vector store singleton
_vector_store_instance = None

def get_vector_store() -> AbstractVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        if settings.VECTOR_DB_TYPE == "faiss" and FAISS_AVAILABLE:
            _vector_store_instance = FAISSVectorStore(dimension=128)
        else:
            _vector_store_instance = MemoryVectorStore(dimension=128)
    return _vector_store_instance
