"""
agents/parser_agent.py

Parser Agent: Specialist responsible for parsing multi-format resume documents
(PDF, DOCX, TXT) into sanitized plain text with layout structure annotations.
Guarantees untrusted input wrapping to prevent prompt injections.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.guardrails.prompt_injection import detect_prompt_injection, wrap_untrusted_data, sanitize_resume_text

logger = logging.getLogger(__name__)


class ParsedResumeOutput(BaseModel):
    """Pydantic-validated output of the Parser Agent."""
    filename: str = Field(..., description="Original filename of the parsed resume")
    file_type: str = Field(..., description="Document type: pdf, docx, txt")
    page_count: int = Field(1, description="Total number of pages/sections detected")
    clean_text: str = Field(..., description="Clean sanitized plain text extracted from document")
    sections_detected: List[str] = Field(default_factory=list, description="Standard sections identified (e.g. Experience, Skills)")
    has_injection_risk: bool = Field(False, description="Whether prompt injection patterns were neutralized")
    untrusted_wrapped_text: str = Field(..., description="Text safely wrapped in boundary tags")


class ParserAgent:
    """Agent that ingests raw resume file bytes or paths and outputs clean structured text."""

    SECTION_HEADERS = [
        "experience", "work history", "employment", "skills", "technical skills",
        "education", "certifications", "projects", "summary", "profile", "contact",
    ]

    def parse_text(self, text: str, filename: str = "document.txt") -> ParsedResumeOutput:
        """Parse raw text content."""
        clean = sanitize_resume_text(text)
        has_risk, _ = detect_prompt_injection(text)
        sections = self._detect_sections(clean)

        return ParsedResumeOutput(
            filename=filename,
            file_type="txt",
            page_count=max(1, len(clean.split("\n\n\n"))),
            clean_text=clean,
            sections_detected=sections,
            has_injection_risk=has_risk,
            untrusted_wrapped_text=wrap_untrusted_data(clean),
        )

    def parse_pdf(self, file_bytes: bytes, filename: str = "resume.pdf") -> ParsedResumeOutput:
        """Parse PDF document using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append(text)
            
            raw_text = "\n\n--- Page Break ---\n\n".join(pages_text)
            clean = sanitize_resume_text(raw_text)
            has_risk, _ = detect_prompt_injection(raw_text)
            sections = self._detect_sections(clean)

            return ParsedResumeOutput(
                filename=filename,
                file_type="pdf",
                page_count=len(reader.pages) or 1,
                clean_text=clean,
                sections_detected=sections,
                has_injection_risk=has_risk,
                untrusted_wrapped_text=wrap_untrusted_data(clean),
            )
        except Exception as e:
            logger.warning("PDF parsing fallback due to: %s", e)
            # Fallback to UTF-8 lossy decode
            fallback_text = file_bytes.decode("utf-8", errors="ignore")
            return self.parse_text(fallback_text, filename=filename)

    def parse_docx(self, file_bytes: bytes, filename: str = "resume.docx") -> ParsedResumeOutput:
        """Parse DOCX document using python-docx."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paras.append(row_text)

            raw_text = "\n\n".join(paras)
            clean = sanitize_resume_text(raw_text)
            has_risk, _ = detect_prompt_injection(raw_text)
            sections = self._detect_sections(clean)

            return ParsedResumeOutput(
                filename=filename,
                file_type="docx",
                page_count=max(1, len(paras) // 15),
                clean_text=clean,
                sections_detected=sections,
                has_injection_risk=has_risk,
                untrusted_wrapped_text=wrap_untrusted_data(clean),
            )
        except Exception as e:
            logger.warning("DOCX parsing fallback due to: %s", e)
            fallback_text = file_bytes.decode("utf-8", errors="ignore")
            return self.parse_text(fallback_text, filename=filename)

    def parse_file(self, file_bytes: bytes, filename: str) -> ParsedResumeOutput:
        """Auto-detects file extension and routes to appropriate parser."""
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return self.parse_pdf(file_bytes, filename)
        elif ext in [".docx", ".doc"]:
            return self.parse_docx(file_bytes, filename)
        else:
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = file_bytes.decode("latin-1", errors="ignore")
            return self.parse_text(text, filename)

    def _detect_sections(self, text: str) -> List[str]:
        """Detect which resume sections exist in the text."""
        lower_text = text.lower()
        found = []
        for header in self.SECTION_HEADERS:
            if re.search(rf"\b{re.escape(header)}\b", lower_text):
                found.append(header.title())
        return found
