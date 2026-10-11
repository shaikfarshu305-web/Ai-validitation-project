import hashlib
import threading
import time
import re
from typing import List, Optional, Dict, Tuple

from app.rag.embeddings import embedder
from app.rag.vector_store import get_vector_store
from app.schemas.evaluation_schemas import RetrievedChunk
from app.config import settings

# ── Retrieval result cache ────────────────────────────────────────────────────
# Cache key: (query_hash, top_k, dataset, min_score)  → (chunks, timestamp)
_RETRIEVAL_CACHE: Dict[str, Tuple[List[RetrievedChunk], float]] = {}
_RETRIEVAL_CACHE_LOCK = threading.Lock()
_RETRIEVAL_CACHE_TTL = 300.0   # 5 minutes
_RETRIEVAL_CACHE_MAX = 256
_QUESTION_STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how", "does",
    "did", "do", "is", "are", "was", "were", "the", "a", "an", "of", "to", "in",
    "on", "for", "with", "and", "or", "explain", "describe", "tell", "about", "cause",
    "created",
}


def _has_question_overlap(query: str, candidate: Dict[str, str]) -> bool:
    query_terms = {
        token for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) >= 3 and token not in _QUESTION_STOP_WORDS
    }
    if not query_terms:
        return True

    candidate_text = f"{candidate.get('title', '')} {candidate.get('chunk_text', '')}"
    candidate_terms = set(re.findall(r"[a-z0-9]+", candidate_text.lower()))
    matched = query_terms & candidate_terms
    return bool(matched) and len(matched) / len(query_terms) >= 0.5


def _retrieval_cache_key(query: str, top_k: int, dataset: Optional[str], min_score: float) -> str:
    raw = f"{query}|{top_k}|{dataset}|{min_score}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def retrieve_evidence(
    query: str,
    top_k: Optional[int] = None,
    dataset: Optional[str] = None,
    min_score: Optional[float] = None,
) -> List[RetrievedChunk]:
    """
    Retrieve semantically relevant knowledge chunks from the FAISS vector store.

    Performance optimizations:
    - Embedding is cached by query text (see embeddings.py)
    - Retrieval results are cached by (query, top_k, dataset, min_score) for TTL=5min
    - Vector store singleton is reused — not re-initialized per call
    """
    if not query or not query.strip():
        return []

    k = top_k if top_k is not None else settings.DEFAULT_RETRIEVAL_TOP_K
    threshold = min_score if min_score is not None else settings.SIMILARITY_THRESHOLD

    cache_key = _retrieval_cache_key(query, k, dataset, threshold)
    now = time.monotonic()

    # Check cache
    with _RETRIEVAL_CACHE_LOCK:
        if cache_key in _RETRIEVAL_CACHE:
            cached_chunks, cached_at = _RETRIEVAL_CACHE[cache_key]
            if (now - cached_at) < _RETRIEVAL_CACHE_TTL:
                return cached_chunks

    # Miss — compute embedding and search
    vector_store = get_vector_store()
    q_vec = embedder.embed_text(query)       # embedding itself is cached
    search_results = vector_store.search(q_vec, top_k=k * 8, dataset=dataset)

    retrieved: List[RetrievedChunk] = []
    for meta, score in search_results:
        if not _has_question_overlap(query, meta):
            continue
        if score >= threshold or (len(retrieved) == 0 and score > 0.05):
            retrieved.append(
                RetrievedChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    dataset=meta.get("dataset", "KnowledgeBase"),
                    title=meta.get("title", "Reference Context"),
                    text=meta.get("chunk_text", ""),
                    similarity_score=round(float(score), 4),
                    source=meta.get("source", "Benchmark Corpus"),
                    metadata=meta.get("metadata", {}),
                )
            )
            if len(retrieved) >= k:
                break

    # Store in cache
    with _RETRIEVAL_CACHE_LOCK:
        if len(_RETRIEVAL_CACHE) >= _RETRIEVAL_CACHE_MAX:
            oldest = next(iter(_RETRIEVAL_CACHE))
            del _RETRIEVAL_CACHE[oldest]
        _RETRIEVAL_CACHE[cache_key] = (retrieved, now)

    return retrieved
