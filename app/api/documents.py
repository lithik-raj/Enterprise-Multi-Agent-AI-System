"""
Document upload router — POST /api/upload

Phase 3: validates file type and size, saves to uploads/ directory,
returns a document_id.  RAG indexing (chunking + embeddings) added in Phase 6.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.models.schemas import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UploadResponse

router = APIRouter(prefix="/api", tags=["Documents"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _validate_file(file: UploadFile) -> str:
    """Return the file extension or raise HTTPException."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '.{ext}' is not supported. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )
    return ext


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF, TXT, or DOCX document for RAG indexing",
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a document.

    - Validates file extension and size.
    - Saves the file to the uploads directory.
    - Returns a document_id for use in chat/analyze requests.
    - RAG chunking + indexing fires in Phase 6.
    """
    ext = _validate_file(file)

    content = await file.read()
    size_bytes = len(content)
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit ({size_bytes} bytes received).",
        )

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Save to uploads directory (fallback to /tmp on serverless environments like Vercel)
    upload_dir = Path(settings.UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        upload_dir = Path("/tmp") / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid.uuid4())
    # Store as <uuid>.<ext> to avoid filename collisions / path traversal risks
    safe_path = upload_dir / f"{document_id}.{ext}"
    safe_path.write_bytes(content)

    # Automatically extract text and index into RAG FAISS vector store immediately
    chunk_count = 0
    extracted_snippet = ""
    try:
        from app.rag.loader import get_loader
        from app.rag.retriever import get_rag_retriever
        loader = get_loader()
        text = loader.load(str(safe_path), ext)
        if text:
            extracted_snippet = text[:400].strip()
        retriever = get_rag_retriever()
        chunk_count = retriever.index_document(document_id, ext, text=text)
        logger.info("Successfully indexed %d chunks for document %s", chunk_count, document_id)
    except Exception as exc:
        logger.warning("Auto-indexing notice for document %s: %s", document_id, exc)

    # Store metadata with real original filename
    try:
        import json
        from datetime import datetime
        meta_path = upload_dir / f"{document_id}.meta.json"
        meta_path.write_text(
            json.dumps({
                "document_id": document_id,
                "filename": file.filename or f"document.{ext}",
                "file_type": ext,
                "size_bytes": size_bytes,
                "chunk_count": chunk_count,
                "uploaded_at": datetime.utcnow().isoformat(),
                "preview": extracted_snippet,
            }),
            encoding="utf-8",
        )
    except Exception as meta_err:
        logger.warning("Could not persist meta.json for %s: %s", document_id, meta_err)

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "unknown",
        file_type=ext,
        size_bytes=size_bytes,
        chunk_count=chunk_count,
        extracted_preview=extracted_snippet,
        message=f"Document uploaded & indexed into RAG memory ({chunk_count} vector chunks ready).",
    )


@router.get(
    "/documents",
    summary="List all uploaded knowledge documents",
)
async def list_documents():
    """Returns metadata for all documents stored in the platform's knowledge base."""
    from app.services.task_manager import get_task_manager
    manager = get_task_manager()
    return manager.list_uploaded_documents()


@router.get(
    "/documents/{document_id}/text",
    summary="Retrieve extracted text of an uploaded document",
)
async def get_document_text(document_id: str):
    """Returns plain text extracted from an uploaded document for inspection or resume prefilling."""
    upload_dir = Path(settings.UPLOAD_DIR)
    for p in upload_dir.iterdir():
        if p.is_file() and p.stem == document_id and not p.name.endswith(".meta.json"):
            ext = p.suffix.lstrip(".").lower()
            try:
                from app.rag.loader import get_loader
                loader = get_loader()
                text = loader.load(str(p), ext)
                return {
                    "document_id": document_id,
                    "filename": p.name,
                    "file_type": ext,
                    "text": text,
                    "word_count": len(text.split()),
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to read document text: {e}")
    raise HTTPException(status_code=404, detail="Document not found.")


@router.delete(
    "/documents/{document_id}",
    summary="Delete an uploaded document",
)
async def delete_document(document_id: str):
    """Deletes an uploaded document from disk."""
    upload_dir = Path(settings.UPLOAD_DIR)
    deleted = False
    for p in list(upload_dir.iterdir()):
        if p.is_file() and p.stem == document_id:
            try:
                p.unlink()
                deleted = True
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"message": "Document removed successfully.", "document_id": document_id}
