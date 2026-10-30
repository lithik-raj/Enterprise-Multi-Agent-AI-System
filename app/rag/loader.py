"""
Document Loader.

Extracts plain text from physical files (TXT, PDF, DOCX).
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentLoader:
    def __init__(self):
        try:
            import pypdf
            import docx
            self.pypdf = pypdf
            self.docx = docx
        except ImportError as exc:
            raise RuntimeError("RAG dependencies not installed. Run: pip install pypdf python-docx") from exc

    def load(self, file_path: str, ext: str) -> str:
        """Extract text from the file at file_path based on its extension."""
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found: %s", file_path)
            return ""

        ext = ext.lower()
        if ext == "txt":
            return self._load_txt(path)
        elif ext == "pdf":
            return self._load_pdf(path)
        elif ext == "docx":
            return self._load_docx(path)
        else:
            logger.warning("Unsupported extension: %s", ext)
            return ""

    def _load_txt(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to standard open with error ignore
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def _load_pdf(self, path: Path) -> str:
        text_parts = []
        try:
            reader = self.pypdf.PdfReader(str(path))
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        except Exception as e:
            logger.error("Error reading PDF %s: %s", path, e)
        return "\n".join(text_parts)

    def _load_docx(self, path: Path) -> str:
        text_parts = []
        try:
            doc = self.docx.Document(str(path))
            for para in doc.paragraphs:
                text_parts.append(para.text)
        except Exception as e:
            logger.error("Error reading DOCX %s: %s", path, e)
        return "\n".join(text_parts)

_loader = None
def get_loader() -> DocumentLoader:
    global _loader
    if _loader is None:
        _loader = DocumentLoader()
    return _loader
