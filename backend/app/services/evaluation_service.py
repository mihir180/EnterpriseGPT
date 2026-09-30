"""
RAG evaluation.

Runs a labeled test set (question + ground_truth) through the live RAG
pipeline and scores it. If `ragas` + a configured judge LLM are available,
we use real RAGAS metrics (faithfulness, answer_relevancy,
context_precision). Otherwise we fall back to cheap heuristic proxies so
the eval endpoint still works out of the box with a local Ollama-only
setup that has no OpenAI key for RAGAS's judge model.

The heuristic fallback is clearly labeled as such in the response — it is
NOT a substitute for real RAGAS scores, just a directional sanity check
(token-overlap based) for environments without a judge LLM configured.
"""
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.services import rag_service

logger = logging.getLogger(__name__)
settings = get_settings()

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class EvalCase:
    question: str
    ground_truth: str


@dataclass
class EvalCaseResult:
    question: str
    generated_answer: str
    ground_truth: str
    context_used: bool
    faithfulness: float
    answer_relevancy: float
    context_precision: float


@dataclass
class EvalReport:
    engine: str  # "ragas" or "heuristic"
    cases: list[EvalCaseResult] = field(default_factory=list)
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_precision: float = 0.0


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _overlap_ratio(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _heuristic_score(answer: str, ground_truth: str, context: str) -> tuple[float, float, float]:
    faithfulness = _overlap_ratio(answer, context) if context else 0.0
    answer_relevancy = _overlap_ratio(answer, ground_truth)
    context_precision = _overlap_ratio(context, ground_truth) if context else 0.0
    return round(faithfulness, 3), round(answer_relevancy, 3), round(context_precision, 3)


def _ragas_available() -> bool:
    try:
        import ragas  # noqa: F401
        return bool(settings.ragas_judge_llm_api_key)
    except ImportError:
        return False


async def _score_with_ragas(cases: list[dict]) -> list[tuple[float, float, float]]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, faithfulness

    dataset = Dataset.from_list(cases)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
    )
    df = result.to_pandas()
    return list(
        zip(
            df["faithfulness"].tolist(),
            df["answer_relevancy"].tolist(),
            df["context_precision"].tolist(),
        )
    )


async def run_evaluation(
    db: AsyncSession, user: User, cases: list[EvalCase]
) -> EvalReport:
    raw_cases = []
    for case in cases:
        result = await rag_service.answer_question(db=db, user=user, question=case.question)
        context = rag_service._build_context(result.sources)
        raw_cases.append(
            {
                "question": case.question,
                "answer": result.answer,
                "contexts": [c.content for c in result.sources] or [""],
                "ground_truth": case.ground_truth,
                "context_used": result.context_used,
                "_context_text": context,
            }
        )

    use_ragas = _ragas_available()
    if use_ragas:
        try:
            scores = await _score_with_ragas(
                [
                    {
                        "question": c["question"],
                        "answer": c["answer"],
                        "contexts": c["contexts"],
                        "ground_truth": c["ground_truth"],
                    }
                    for c in raw_cases
                ]
            )
            engine = "ragas"
        except Exception:
            logger.exception("RAGAS scoring failed, falling back to heuristic")
            use_ragas = False

    if not use_ragas:
        scores = [
            _heuristic_score(c["answer"], c["ground_truth"], c["_context_text"])
            for c in raw_cases
        ]
        engine = "heuristic"

    report = EvalReport(engine=engine)
    for c, (faith, rel, prec) in zip(raw_cases, scores):
        report.cases.append(
            EvalCaseResult(
                question=c["question"],
                generated_answer=c["answer"],
                ground_truth=c["ground_truth"],
                context_used=c["context_used"],
                faithfulness=float(faith),
                answer_relevancy=float(rel),
                context_precision=float(prec),
            )
        )

    n = len(report.cases) or 1
    report.avg_faithfulness = round(sum(c.faithfulness for c in report.cases) / n, 3)
    report.avg_answer_relevancy = round(sum(c.answer_relevancy for c in report.cases) / n, 3)
    report.avg_context_precision = round(sum(c.context_precision for c in report.cases) / n, 3)
    return report
