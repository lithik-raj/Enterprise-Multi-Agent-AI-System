"""
Vector Store using FAISS.

Stores chunk embeddings and their corresponding text. Allows for top-k similarity search.
Normally, FAISS indexes would be persisted to disk, but for this demo/portfolio, we keep an on-disk index
that we load/save or an in-memory index depending on complexity. 
We'll implement a simple persistent FAISS index.
"""

import os
import json
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorStore:
    def __init__(self, dimension: int):
        try:
            import faiss
            import numpy as np
            self.faiss = faiss
            self.np = np
        except ImportError as exc:
            raise RuntimeError("faiss is not installed. Run: pip install faiss-cpu") from exc
            
        self.dimension = dimension
        self.store_dir = Path(settings.VECTOR_STORE_DIR)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.store_dir / "index.faiss"
        self.meta_path = self.store_dir / "meta.json"
        
        self.index = None
        self.metadata = {}  # idx -> {document_id: str, text: str}
        self.current_idx = 0
        
        self._load()

    def _load(self):
        """Load index and metadata from disk if they exist."""
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = self.faiss.read_index(str(self.index_path))
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    # JSON keys are strings, convert to int
                    raw_meta = json.load(f)
                    self.metadata = {int(k): v for k, v in raw_meta.items()}
                self.current_idx = max(self.metadata.keys(), default=-1) + 1
                logger.info("Loaded FAISS index with %d vectors", self.current_idx)
            except Exception as e:
                logger.error("Failed to load FAISS index: %s. Creating new.", e)
                self._init_new_index()
        else:
            self._init_new_index()

    def _init_new_index(self):
        """Create a fresh L2 index."""
        self.index = self.faiss.IndexFlatL2(self.dimension)
        self.metadata = {}
        self.current_idx = 0
        
    def _save(self):
        """Persist index and metadata to disk."""
        self.faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def add_chunks(self, document_id: str, chunks: list[str], embeddings: list[list[float]]):
        """Add chunks to the vector store."""
        if not chunks or not getattr(self, "index", None):
            return
            
        vectors = self.np.array(embeddings, dtype=self.np.float32)
        
        # Add to FAISS
        self.index.add(vectors)
        
        # Save metadata
        for chunk in chunks:
            self.metadata[self.current_idx] = {
                "document_id": document_id,
                "text": chunk
            }
            self.current_idx += 1
            
        self._save()

    def search(self, query_embedding: list[float], top_k: int = 3, document_ids: list[str] = None) -> list[dict]:
        """
        Search for top_k most similar chunks.
        Optionally filter by a list of document_ids.
        """
        if getattr(self, "index", None) is None or self.index.ntotal == 0:
            return []
            
        vector = self.np.array([query_embedding], dtype=self.np.float32)
        
        # FAISS doesn't do native metadata filtering on IndexFlatL2 easily,
        # so we fetch more results and filter in Python.
        fetch_k = max(top_k * 5, 20) if document_ids else top_k
        fetch_k = min(fetch_k, self.index.ntotal)
        
        distances, indices = self.index.search(vector, fetch_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                break # FAISS returns -1 if not enough results
                
            idx_meta = self.metadata.get(idx)
            if not idx_meta:
                continue
                
            doc_id = idx_meta["document_id"]
            
            # Apply filter
            if document_ids and doc_id not in document_ids:
                continue
                
            results.append({
                "document_id": doc_id,
                "text": idx_meta["text"],
                "distance": float(distances[0][i])
            })
            
            if len(results) >= top_k:
                break
                
        return results

_vector_store = None
def get_vector_store(dimension: int = 384) -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(dimension)
    return _vector_store
