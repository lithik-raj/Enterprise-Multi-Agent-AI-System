"""
Text Chunker.

Breaks long text into smaller overlapping chunks suitable for embeddings.
"""

import logging

logger = logging.getLogger(__name__)

class Chunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> list[str]:
        """
        Chunk text using a simple character-level sliding window.
        In a more advanced setup, this would use a recursive character splitter or semantic splitter.
        """
        if not text:
            return []

        # Basic cleanup
        text = " ".join(text.split())
        
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            
            # If we're not at the end of the text, try to find a natural break (period or space)
            if end < text_len:
                # Look backwards for a period
                last_period = text.rfind(".", start, end)
                if last_period != -1 and last_period > start + (self.chunk_size // 2):
                    end = last_period + 1
                else:
                    # Look backwards for a space
                    last_space = text.rfind(" ", start, end)
                    if last_space != -1 and last_space > start + (self.chunk_size // 2):
                        end = last_space

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move forward by chunk size minus overlap
            start = end - self.overlap

        return chunks

_chunker = None
def get_chunker() -> Chunker:
    global _chunker
    if _chunker is None:
        _chunker = Chunker()
    return _chunker
