import re
from dataclasses import dataclass

from app.services.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.extraction_service import ExtractionResult

settings = get_settings()


@dataclass
class Chunk:
    index: int
    content: str
    page_number: int | None


def clean_text(text: str) -> str:
    """Normalize whitespace and strip common PDF extraction artifacts."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_extraction_result(
    result: ExtractionResult,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """
    Split extracted text into overlapping chunks, preserving page numbers
    where available (PDFs) so citations can point to a specific page.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Chunk] = []
    index = 0

    for page in result.pages:
        cleaned = clean_text(page.text)
        if not cleaned:
            continue
        for piece in splitter.split_text(cleaned):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(Chunk(index=index, content=piece, page_number=page.page_number))
            index += 1

    return chunks
