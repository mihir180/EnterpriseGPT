"""
Phase 4 RAG orchestration.

Pipeline:
  question
    -> ACL: which documents may this user see at all?
    -> router agent: which department specialist should answer?
    -> narrow candidates to that department's documents (still inside ACL)
    -> hybrid search (vector + BM25, fused with Reciprocal Rank Fusion)
    -> specialist system prompt + context -> llm_service.generate_answer
    -> citations + persisted ChatQuery row (for analytics)
"""
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatQuery
from app.models.document import Document
from app.models.user import Department, User
from app.services import acl_service, agent_service, bm25_service
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)

VECTOR_CANDIDATE_K = 20
BM25_CANDIDATE_K = 20
FINAL_TOP_K = 6
RRF_K = 60  # standard RRF smoothing constant


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    content: str
    page_number: int | None
    score: float


@dataclass
class RagResult:
    answer: str
    sources: list[RetrievedChunk]
    context_used: bool
    department: Department
    agent_used: str
    retrieval_mode: str


def _reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = RRF_K
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked_ids in ranked_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


async def _hybrid_search(
    db: AsyncSession,
    query: str,
    allowed_document_ids: list[uuid.UUID] | None,
) -> tuple[list[RetrievedChunk], str]:
    """Returns (ranked chunks, retrieval_mode actually used)."""
    query_vector = embedding_service.embed_query(query)

    vector_hits = vector_store_service.search(
        query_vector=query_vector,
        top_k=VECTOR_CANDIDATE_K,
        document_ids=[str(d) for d in allowed_document_ids] if allowed_document_ids is not None else None,
    )
    vector_lookup: dict[str, RetrievedChunk] = {
        str(hit.id): RetrievedChunk(
            chunk_id=str(hit.id),
            document_id=str(hit.payload.get("document_id")),
            filename=hit.payload.get("filename", "unknown"),
            content=hit.payload.get("content") or hit.payload.get("text", ""),
            page_number=hit.payload.get("page_number"),
            score=float(hit.score),
        )
        for hit in vector_hits
    }
    vector_ranked_ids = list(vector_lookup.keys())

    try:
        bm25_hits = await bm25_service.bm25_search(
            db=db, query=query, document_ids=allowed_document_ids, top_k=BM25_CANDIDATE_K
        )
        bm25_lookup: dict[str, RetrievedChunk] = {}
        for hit in bm25_hits:
            bm25_lookup[str(hit.chunk_id)] = RetrievedChunk(
                chunk_id=str(hit.chunk_id),
                document_id=str(hit.document_id),
                filename="",  # filled in below from Document lookup if needed
                content=hit.content,
                page_number=hit.page_number,
                score=hit.score,
            )
        bm25_ranked_ids = list(bm25_lookup.keys())
        retrieval_mode = "hybrid"
    except Exception:
        logger.exception("BM25 search failed, falling back to vector-only retrieval")
        bm25_lookup, bm25_ranked_ids = {}, []
        retrieval_mode = "vector"

    fused_scores = _reciprocal_rank_fusion([vector_ranked_ids, bm25_ranked_ids])
    if not fused_scores:
        return [], retrieval_mode

    ordered_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)[:FINAL_TOP_K]

    results: list[RetrievedChunk] = []
    for cid in ordered_ids:
        chunk = vector_lookup.get(cid) or bm25_lookup.get(cid)
        if chunk is None:
            continue
        chunk.score = fused_scores[cid]
        if not chunk.filename:
            doc = await db.get(Document, uuid.UUID(chunk.document_id))
            chunk.filename = doc.filename if doc else "unknown"
        results.append(chunk)
    return results, retrieval_mode


def _build_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for c in chunks:
        page = f", page {c.page_number}" if c.page_number else ""
        blocks.append(f"[Source: {c.filename}{page}]\n{c.content}")
    return "\n\n---\n\n".join(blocks)


async def answer_question(
    db: AsyncSession,
    user: User,
    question: str,
    department_override: Department | None = None,
    document_ids_filter: list[uuid.UUID] | None = None,
) -> RagResult:
    # 1. ACL: what can this user see at all?
    accessible_ids = await acl_service.get_accessible_document_ids(db, user)

    # Manual document filter (from the request), intersected with ACL.
    if document_ids_filter is not None:
        if accessible_ids is None:
            accessible_ids = document_ids_filter
        else:
            accessible_set = set(accessible_ids)
            accessible_ids = [d for d in document_ids_filter if d in accessible_set]

    # 2. Route to a specialist agent.
    department = department_override or await agent_service.classify_department(question)

    # 3. Narrow candidates to that department's documents, but only if doing
    #    so wouldn't wipe out the corpus entirely (falls back to the full
    #    ACL-accessible set so a mistagged/untagged corpus still works).
    dept_doc_ids = await acl_service.get_department_document_ids(db, department.value)
    if dept_doc_ids:
        if accessible_ids is None:
            candidate_ids: list[uuid.UUID] | None = dept_doc_ids
        else:
            dept_set = set(dept_doc_ids)
            candidate_ids = [d for d in accessible_ids if d in dept_set]
            if not candidate_ids:
                candidate_ids = accessible_ids  # fall back rather than return nothing
    else:
        candidate_ids = accessible_ids

    # 4. Hybrid retrieval within the ACL+department candidate set.
    chunks, retrieval_mode = await _hybrid_search(db, question, candidate_ids)
    context_used = len(chunks) > 0

    # 5. Generate.
    system_prompt = agent_service.get_system_prompt(department)
    context = _build_context(chunks) if context_used else ""
    if context_used:
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"
        answer = await llm_service.generate_answer(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
    else:
        answer = (
            "I don't have any information on that in the documents I have access to. "
            "Please check with the relevant team or try rephrasing your question."
        )

    result = RagResult(
        answer=answer,
        sources=chunks,
        context_used=context_used,
        department=department,
        agent_used=agent_service.agent_name(department),
        retrieval_mode=retrieval_mode,
    )

    # 6. Persist for analytics/history.
    log_entry = ChatQuery(
        user_id=user.id,
        question=question,
        answer=answer,
        sources=[
            {
                "document_id": c.document_id,
                "chunk_id": c.chunk_id,
                "filename": c.filename,
                "page_number": c.page_number,
                "score": c.score,
            }
            for c in chunks
        ],
        context_used=context_used,
        department=department.value,
        agent_used=result.agent_used,
        retrieval_mode=retrieval_mode,
    )
    db.add(log_entry)
    await db.commit()

    return result
