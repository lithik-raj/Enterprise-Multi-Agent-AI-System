"""
Central RAG Retriever Service.
Ties together loader, chunker, embeddings, and vector store.
"""

import logging
import os
from pathlib import Path

from app.config import get_settings
from app.rag.loader import get_loader
from app.rag.chunker import get_chunker
from app.rag.embeddings import get_embedding_service
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

class RagRetriever:
    def __init__(self):
        # We lazy load/fetch singletons
        pass

    def index_document(self, document_id: str, file_type: str, text: str | None = None) -> int:
        """
        Process a saved file: Load (if text not passed) -> Chunk -> Embed -> Store.
        Returns the number of chunks created.
        """
        if text is None:
            file_path = Path(settings.UPLOAD_DIR) / f"{document_id}.{file_type}"
            loader = get_loader()
            text = loader.load(str(file_path), file_type)
        if not text:
            return 0
            
        chunker = get_chunker()
        chunks = chunker.chunk_text(text)
        if not chunks:
            return 0
            
        embedder = get_embedding_service()
        embeddings = embedder.embed_batch(chunks)
        
        vstore = get_vector_store(embedder.dimension)
        vstore.add_chunks(document_id, chunks, embeddings)
        
        logger.info("Indexed %d chunks for document %s", len(chunks), document_id)
        return len(chunks)

    def search_context(self, query: str, document_ids: list[str] = None, top_k: int = 3) -> list[str]:
        """
        Search indexed documents for context relevant to the query.
        Returns a list of text chunks.
        """
        if not query:
            return []
            
        embedder = get_embedding_service()
        query_embedding = embedder.embed_text(query)
        
        vstore = get_vector_store(embedder.dimension)
        results = vstore.search(query_embedding, top_k=top_k, document_ids=document_ids)
        
        # Just return the text strings for prompt insertion
        return [res["text"] for res in results]

_rag_retriever = None
def get_rag_retriever() -> RagRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RagRetriever()
    return _rag_retriever
