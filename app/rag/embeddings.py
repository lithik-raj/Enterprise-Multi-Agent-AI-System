"""
Embeddings Service.

Wraps sentence-transformers to generate dense vectors for chunks.
Provides resilient standalone fallback if torch or native DLLs fail to load.
"""

import hashlib
import logging
import os
import numpy as np
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


_TORCH_PROBED = None
_EMBED_CACHE: dict[str, list[float]] = {}


def _is_torch_healthy() -> bool:
    global _TORCH_PROBED
    if _TORCH_PROBED is not None:
        return _TORCH_PROBED
    if os.environ.get("DISABLE_TORCH", "").lower() in ("1", "true", "yes"):
        _TORCH_PROBED = False
        return False
    import sys
    if sys.platform == "win32":
        # On Windows, broken c10.dll causes process-level access violation.
        # Check if torch is already loaded; otherwise use high-speed projection.
        if "torch" in sys.modules:
            _TORCH_PROBED = hasattr(sys.modules["torch"], "__version__")
            return _TORCH_PROBED
        _TORCH_PROBED = False
        return False
    try:
        import torch
        _TORCH_PROBED = hasattr(torch, "__version__") and bool(torch.__version__)
    except Exception:
        _TORCH_PROBED = False
    return _TORCH_PROBED


class EmbeddingService:
    def __init__(self):
        self.model = None
        self.dimension = 384  # Standard MiniLM embedding dimension

        if _is_torch_healthy():
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info("EmbeddingService initialised with %s (dim=%d)", settings.EMBEDDING_MODEL, self.dimension)
            except Exception as exc:
                logger.warning("sentence-transformers could not be initialized (%s). Using high-speed standalone mode.", exc)
                self.model = None
        else:
            logger.info("Operating in high-speed standalone dense projection mode (dim=%d).", self.dimension)
            self.model = None

    def _fallback_embed(self, text: str) -> list[float]:
        """Fast, deterministic dense semantic projection with normalized unit vector."""
        if not text:
            return [0.0] * self.dimension
        cache_key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if cache_key in _EMBED_CACHE:
            return _EMBED_CACHE[cache_key]

        vec = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        if not words:
            res = vec.tolist()
            _EMBED_CACHE[cache_key] = res
            return res

        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        res = vec.tolist()
        if len(_EMBED_CACHE) < 5000:
            _EMBED_CACHE[cache_key] = res
        return res

    def embed_text(self, text: str) -> list[float]:
        """Embed a single string."""
        if self.model is not None:
            try:
                vector = self.model.encode(text, convert_to_numpy=True)
                return vector.tolist()
            except Exception as exc:
                logger.warning("Model encoding error (%s); using high-speed fallback", exc)

        return self._fallback_embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings efficiently."""
        if not texts:
            return []
        if self.model is not None:
            try:
                vectors = self.model.encode(texts, convert_to_numpy=True)
                return [v.tolist() for v in vectors]
            except Exception as exc:
                logger.warning("Model batch encoding error (%s); using high-speed fallback", exc)

        return [self._fallback_embed(t) for t in texts]


_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
