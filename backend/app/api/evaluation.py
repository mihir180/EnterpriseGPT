from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_db
from app.models.user import User
from app.services.evaluation_service import EvalCase, run_evaluation

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


class EvalCaseIn(BaseModel):
    question: str
    ground_truth: str = Field(..., description="The known-correct answer, for scoring.")


class EvalRunRequest(BaseModel):
    cases: list[EvalCaseIn]


@router.post("/run")
async def run_rag_evaluation(
    payload: EvalRunRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs each case through the live RAG pipeline (as the requesting admin
    user — so results reflect that admin's document access) and scores
    faithfulness / answer relevancy / context precision.

    Uses real RAGAS metrics if `ragas` is installed and RAGAS_JUDGE_LLM_API_KEY
    is set; otherwise falls back to heuristic token-overlap scoring and
    labels the report accordingly (see evaluation_service docstring).
    """
    cases = [EvalCase(question=c.question, ground_truth=c.ground_truth) for c in payload.cases]
    report = await run_evaluation(db=db, user=admin, cases=cases)
    return report
