"""
Phase 6 — RAG Pipeline Tests.
Run with:   pytest tests/test_rag.py -v
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.rag.chunker import Chunker
from app.rag.embeddings import EmbeddingService
from app.rag.loader import DocumentLoader
from app.rag.vector_store import VectorStore
# from app.rag.retriever import RagRetriever # tests usually mock lower level 

# ── Chunker Tests ─────────────────────────────────────────────────────────────

def test_chunker_basic():
    chunker = Chunker(chunk_size=10, overlap=2)
    # length 25
    text = "abcdefghijklmnopqrstuvwxy"
    chunks = chunker.chunk_text(text)
    # chunk_size is 10, overlap is 2, move by 8.
    # 0-10: 'abcdefghij'
    # 8-18: 'ijklmnopqr'
    # 16-25: 'qrstuvwxy'
    assert chunks[0] == "abcdefghij"
    assert chunks[1] == "ijklmnopqr"
    assert chunks[2] == "qrstuvwxy"

def test_chunker_empty():
    chunker = Chunker()
    assert chunker.chunk_text("") == []

# ── Loader Tests ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_loader():
    with patch('app.rag.loader.get_loader') as mock:
        loader = DocumentLoader()
        loader._load_pdf = MagicMock(return_value="pdf content")
        loader._load_docx = MagicMock(return_value="docx content")
        return loader

def test_loader_txt(tmp_path):
    loader = DocumentLoader()
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello text file", encoding="utf-8")
    result = loader.load(str(test_file), "txt")
    assert result == "hello text file"

def test_loader_unsupported(tmp_path):
    loader = DocumentLoader()
    test_file = tmp_path / "test.xyz"
    test_file.write_text("hello", encoding="utf-8")
    result = loader.load(str(test_file), "xyz")
    assert result == ""

def test_loader_pdf_mock(mock_loader, tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"dummy")
    result = mock_loader.load(str(test_file), "pdf")
    assert result == "pdf content"

# ── Vector Store & Embeddings Mock Tests ─────────────────────────────────────
# We test the pure FAISS wrapper logic with mocked numpy arrays to avoid forcing AI models into memory for CI tests.
# The Embedding Service wrapper is mostly a pass-through to Sentence Transformers.

def test_vector_store_add_and_search(tmp_path):
    with patch("app.rag.vector_store.settings") as mock_settings:
        mock_settings.VECTOR_STORE_DIR = str(tmp_path)
        
        # Dim=2 for simple testing
        store = VectorStore(dimension=2)
        
        # Add a chunk
        doc_id = "doc-123"
        chunks = ["This is context 1", "This is context 2"]
        embeddings = [[0.1, 0.2], [0.9, 0.8]]
        
        store.add_chunks(doc_id, chunks, embeddings)
        assert store.index.ntotal == 2
        
        # Search exact match
        results = store.search([0.1, 0.2], top_k=1)
        assert len(results) == 1
        assert results[0]["document_id"] == "doc-123"
        assert results[0]["text"] == "This is context 1"
        
        # Search with document filter
        results = store.search([0.9, 0.8], top_k=1, document_ids=["doc-wrong"])
        assert len(results) == 0
        
        results = store.search([0.9, 0.8], top_k=1, document_ids=["doc-123"])
        assert len(results) == 1
        assert results[0]["text"] == "This is context 2"
