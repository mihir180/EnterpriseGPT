"""
BM25 keyword search over document chunks, to complement Qdrant's vector
search. Combined via Reciprocal Rank Fusion in rag_service.hybrid_search.

Scope note: this builds an in-memory BM25 index on every call from the
candidate chunk rows in Postgres. That's fine at the scale of an internal
knowledge base (thousands of chunks) but doesn't scale to millions — a
production system would use Qdrant's sparse-vector / server-side BM25
support, or a dedicated search engine like OpenSearch. Flagged here
deliberately rather than hidden, since it's the main scaling caveat of
this implementation.
"""
import re
import uuid
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Hard cap on how many chunks we'll pull into memory for a single BM25 query.
MAX_CANDIDATE_CHUNKS = 5000


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Bm25Hit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    page_number: int | None
    score: float


async def bm25_search(
    db: AsyncSession,
    query: str,
    document_ids: list[uuid.UUID] | None,
    top_k: int = 20,
) -> list[Bm25Hit]:
    """
    document_ids=None means "search all documents" (admin / no ACL filter).
    document_ids=[] means "no accessible documents" -> returns no hits.
    """
    if document_ids is not None and len(document_ids) == 0:
        return []

    stmt = select(DocumentChunk).limit(MAX_CANDIDATE_CHUNKS)
    if document_ids is not None:
        stmt = select(DocumentChunk).where(
            DocumentChunk.document_id.in_(document_ids)
        ).limit(MAX_CANDIDATE_CHUNKS)

    result = await db.execute(stmt)
    chunks = result.scalars().all()
    if not chunks:
        return []

    corpus_tokens = [_tokenize(c.content) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)

    hits: list[Bm25Hit] = []
    for chunk, score in ranked[:top_k]:
        if score <= 0:
            continue
        hits.append(
            Bm25Hit(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                page_number=chunk.page_number,
                score=float(score),
            )
        )
    return hits
