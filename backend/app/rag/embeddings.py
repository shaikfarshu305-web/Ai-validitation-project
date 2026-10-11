import hashlib
import math
import re
import threading
from typing import List, Dict, Tuple, Optional
import numpy as np

# ── LRU-style embedding cache ─────────────────────────────────────────────────
_EMBED_CACHE: Dict[str, np.ndarray] = {}
_EMBED_CACHE_LOCK = threading.Lock()
_EMBED_CACHE_MAX = 512  # max cached embeddings


class SemanticEmbedder:
    """
    Lightweight, fast, deterministic semantic vector embedder.
    Produces L2-normalized 128-dimensional dense vectors using character & token n-gram
    hashing projections.
    Singleton instance is created at module load — no per-request initialization.
    Embedding results are cached by text hash for repeated queries.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 1]

    def _compute_embedding(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        token_counts: Dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        for token, count in token_counts.items():
            weight = 1.0 + math.log(count)

            # Word-level hash projection
            h_word = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
            idx_word = h_word % self.dimension
            sign_word = 1.0 if (h_word % 2 == 0) else -1.0
            vector[idx_word] += weight * sign_word

            # Character 3-gram subword projections
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    sub = token[i : i + 3]
                    h_sub = int(hashlib.sha256(sub.encode("utf-8")).hexdigest()[:8], 16)
                    idx_sub = h_sub % self.dimension
                    sign_sub = 1.0 if (h_sub % 2 == 0) else -1.0
                    vector[idx_sub] += (weight * 0.4) * sign_sub

        # L2 normalization
        norm = np.linalg.norm(vector)
        if norm > 1e-9:
            vector = vector / norm
        return vector

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string, using in-memory cache for repeated queries."""
        key = self._cache_key(text)
        with _EMBED_CACHE_LOCK:
            if key in _EMBED_CACHE:
                return _EMBED_CACHE[key]

        vec = self._compute_embedding(text)

        with _EMBED_CACHE_LOCK:
            # Evict oldest entry if cache full
            if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
                oldest = next(iter(_EMBED_CACHE))
                del _EMBED_CACHE[oldest]
            _EMBED_CACHE[key] = vec

        return vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed a batch using cache per item — avoids redundant computation."""
        embeddings = [self.embed_text(t) for t in texts]
        return np.array(embeddings, dtype=np.float32)


# ── Module-level singleton — initialized ONCE at server startup ───────────────
embedder = SemanticEmbedder(dimension=128)
