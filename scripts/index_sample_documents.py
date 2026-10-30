"""
scripts/index_sample_documents.py

CLI command to index sample portfolio documents into the local FAISS vector store.
Copies sample documents (Resume, AI_ML_Job, Learning_Roadmap) to uploads/ and indexes them.
Usage:
    python scripts/index_sample_documents.py
"""

import shutil
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add workspace root to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from app.config import get_settings
from app.rag.retriever import get_rag_retriever

settings = get_settings()

SAMPLE_DOCS = [
    ("Resume", "txt"),
    ("AI_ML_Job", "txt"),
    ("Learning_Roadmap", "txt"),
]

def index_sample_documents() -> None:
    source_dir = WORKSPACE_ROOT / "data" / "sample_documents"
    upload_dir = WORKSPACE_ROOT / settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    retriever = get_rag_retriever()
    total_chunks = 0

    print("[*] Ingesting and indexing sample documents into FAISS vector store...")

    for doc_name, ext in SAMPLE_DOCS:
        src = source_dir / f"{doc_name}.{ext}"
        dst = upload_dir / f"{doc_name}.{ext}"

        if src.exists():
            shutil.copyfile(src, dst)
            chunks_count = retriever.index_document(doc_name, ext)
            total_chunks += chunks_count
            print(f"  [+] Indexed '{doc_name}.{ext}': {chunks_count} chunks created")
        else:
            print(f"  [-] Warning: Source file '{src}' not found.")

    print(f"\n[+] Indexing Complete! Total {total_chunks} chunks indexed into FAISS.")
    print(f"Vector store directory: {settings.VECTOR_STORE_DIR}")

if __name__ == "__main__":
    index_sample_documents()
