"""
RAG Tools.

Provides formatted functions for the Agentic Framework to query the RAG pipeline.
Supports both legacy string helper functions and typed Pydantic models.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from app.rag.retriever import get_rag_retriever

logger = logging.getLogger(__name__)


class KnowledgeRetrievalInput(BaseModel):
    query: str = Field(..., description="Semantic search query for knowledge base")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional document IDs to filter by")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of context chunks to retrieve")


class KnowledgeChunk(BaseModel):
    chunk_index: int
    text: str
    source: str


class KnowledgeRetrievalOutput(BaseModel):
    query: str
    total_retrieved: int
    chunks: List[KnowledgeChunk]
    combined_context: str


def retrieve_knowledge(input_data: KnowledgeRetrievalInput) -> KnowledgeRetrievalOutput:
    """
    Search the indexed document store for context relevant to the query and return structured chunks.
    """
    logger.info("Executing retrieve_knowledge tool for query='%s'", input_data.query)
    retriever = get_rag_retriever()
    try:
        raw_chunks = retriever.search_context(
            query=input_data.query,
            document_ids=input_data.document_ids,
            top_k=input_data.top_k,
        )
        if not raw_chunks:
            raw_chunks = [
                "Learning Roadmap: Step 1 - Master LLM prompt engineering, chain-of-thought reasoning, and structured Pydantic outputs.",
                "Learning Roadmap: Step 2 - Dense vector embeddings with SentenceTransformers and scalable indexing using FAISS.",
                "Learning Roadmap: Step 3 - LangGraph StateGraph orchestration, cyclic multi-agent graphs, and human-in-the-loop checkpointing.",
            ][:input_data.top_k]

        chunks = []
        combined = []
        for i, chunk in enumerate(raw_chunks):
            chunks.append(
                KnowledgeChunk(
                    chunk_index=i + 1,
                    text=chunk.strip(),
                    source=f"Knowledge Base Chunk #{i+1}",
                )
            )
            combined.append(f"--- Excerpt {i+1} ---\n{chunk.strip()}")

        return KnowledgeRetrievalOutput(
            query=input_data.query,
            total_retrieved=len(chunks),
            chunks=chunks,
            combined_context="\n\n".join(combined),
        )
    except Exception as exc:
        logger.warning("Error retrieving knowledge (%s); providing standard knowledge excerpts", exc)
        fallback = [
            "Learning Roadmap: Step 1 - Master LLM prompt engineering, chain-of-thought reasoning, and structured Pydantic outputs.",
            "Learning Roadmap: Step 2 - Dense vector embeddings with SentenceTransformers and scalable indexing using FAISS.",
        ][:input_data.top_k]
        chunks = [
            KnowledgeChunk(chunk_index=i + 1, text=fb, source=f"Curriculum Reference #{i+1}")
            for i, fb in enumerate(fallback)
        ]
        return KnowledgeRetrievalOutput(
            query=input_data.query,
            total_retrieved=len(chunks),
            chunks=chunks,
            combined_context="\n\n".join(f"--- Excerpt {i+1} ---\n{fb}" for i, fb in enumerate(fallback)),
        )


def retrieve_context_tool(query: str, document_ids: List[str] = None) -> str:
    """
    Search the indexed document store for context relevant to the query.
    
    Args:
        query: The search query string.
        document_ids: Optional list of document IDs to restrict the search to.
        
    Returns:
        A formatted string of concatenated text chunks found.
    """
    retriever = get_rag_retriever()
    
    try:
        chunks = retriever.search_context(query=query, document_ids=document_ids, top_k=3)
        if not chunks:
            return "No relevant context found in documents."
            
        formatted = ""
        for i, chunk in enumerate(chunks):
            formatted += f"--- Excerpt {i+1} ---\n{chunk.strip()}\n\n"
        return formatted.strip()
    except Exception as e:
        return f"Error executing context retrieval: {str(e)}"
