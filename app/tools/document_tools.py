"""
Document Analysis Tools.

Provides tools for inspecting, analyzing, and extracting structured insights
from uploaded documents (PDF, DOCX, TXT).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.loader import DocumentLoader

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentAnalysisInput(BaseModel):
    document_id: str = Field(..., description="ID or filename of the document to inspect")
    analysis_type: Optional[str] = Field("summary", description="Type of analysis: summary, stats, or text")


class DocumentAnalysisOutput(BaseModel):
    document_id: str
    filename: str
    file_type: str
    word_count: int
    character_count: int
    extracted_text_preview: str
    identified_sections: List[str]
    success: bool
    error_message: Optional[str] = None


def analyze_document(input_data: DocumentAnalysisInput) -> DocumentAnalysisOutput:
    """
    Analyze an uploaded document file, extract its text content and compute structural statistics.
    """
    logger.info("Executing analyze_document tool for doc='%s'", input_data.document_id)
    upload_dir = Path(settings.UPLOAD_DIR)

    # Search for matching file by stem or exact filename
    target_path = None
    if upload_dir.exists():
        for p in upload_dir.iterdir():
            if p.is_file() and (p.stem == input_data.document_id or p.name == input_data.document_id):
                target_path = p
                break

    if not target_path:
        # Check sample documents directory as fallback
        sample_dir = Path("data/sample_documents")
        if sample_dir.exists():
            for p in sample_dir.iterdir():
                if p.is_file() and (p.stem == input_data.document_id or p.name == input_data.document_id):
                    target_path = p
                    break

    if not target_path or not target_path.exists():
        return DocumentAnalysisOutput(
            document_id=input_data.document_id,
            filename=input_data.document_id,
            file_type="unknown",
            word_count=0,
            character_count=0,
            extracted_text_preview="",
            identified_sections=[],
            success=False,
            error_message=f"Document '{input_data.document_id}' not found in upload directory.",
        )

    file_ext = target_path.suffix.lstrip(".").lower()
    loader = DocumentLoader()

    try:
        raw_text = loader.load(str(target_path), file_ext)
        words = raw_text.split()
        word_count = len(words)
        char_count = len(raw_text)

        # Detect common resume/job sections
        potential_sections = [
            "Experience", "Skills", "Education", "Projects", "Requirements",
            "Responsibilities", "Qualifications", "Summary", "About", "Overview"
        ]
        found_sections = [
            sec for sec in potential_sections if sec.lower() in raw_text.lower()
        ]

        preview = raw_text[:400] + ("..." if len(raw_text) > 400 else "")

        return DocumentAnalysisOutput(
            document_id=input_data.document_id,
            filename=target_path.name,
            file_type=file_ext,
            word_count=word_count,
            character_count=char_count,
            extracted_text_preview=preview,
            identified_sections=found_sections,
            success=True,
        )

    except Exception as exc:
        logger.error("Failed to analyze document %s: %s", target_path.name, exc)
        return DocumentAnalysisOutput(
            document_id=input_data.document_id,
            filename=target_path.name,
            file_type=file_ext,
            word_count=0,
            character_count=0,
            extracted_text_preview="",
            identified_sections=[],
            success=False,
            error_message=str(exc),
        )
