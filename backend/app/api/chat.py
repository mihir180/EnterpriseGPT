from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.chat import ChatQueryRead, ChatRequest, ChatResponse, SourceCitation
from app.services import rag_service
from app.core.rate_limit import limiter
from sqlalchemy import select, func
from app.models.chat import ChatQuery

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
@limiter.limit("20/minute")
async def ask_question(
    request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    result = await rag_service.answer_question(
        db=db,
        user=current_user,
        question=payload.question,
        department_override=payload.department,
        document_ids_filter=payload.document_ids,
    )

    return ChatResponse(
        question=payload.question,
        answer=result.answer,
        sources=[
            SourceCitation(
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                filename=c.filename,
                page_number=c.page_number,
                score=round(c.score, 4),
            )
            for c in result.sources
        ],
        context_used=result.context_used,
        department=result.department,
        agent_used=result.agent_used,
        retrieval_mode=result.retrieval_mode,
    )
@router.get("/history")
async def get_chat_history(
    offset: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(
        select(func.count(ChatQuery.id)).where(ChatQuery.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(ChatQuery)
        .where(ChatQuery.user_id == current_user.id)
        .order_by(ChatQuery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()

    return {
        "total": total,
        "items": [ChatQueryRead.model_validate(item) for item in items],
    }
