import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_db
from app.models.chat import ChatQuery
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    DailyCount,
    DepartmentCount,
    TopicCount,
    UserActivity,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "who", "how",
    "when", "where", "why", "do", "does", "did", "can", "could", "should",
    "would", "to", "of", "in", "on", "for", "and", "or", "my", "me", "i",
    "you", "your", "we", "our", "it", "this", "that", "with", "have", "has",
    "please", "tell", "about",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = 7,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    total_result = await db.execute(select(func.count(ChatQuery.id)))
    total_questions = total_result.scalar_one()

    failed_result = await db.execute(
        select(func.count(ChatQuery.id)).where(ChatQuery.context_used.is_(False))
    )
    failed_queries = failed_result.scalar_one()
    failure_rate = round(failed_queries / total_questions, 3) if total_questions else 0.0

    since = datetime.now(timezone.utc) - timedelta(days=days)
    daily_result = await db.execute(
        select(
            func.date_trunc("day", ChatQuery.created_at).label("day"),
            func.count(ChatQuery.id),
        )
        .where(ChatQuery.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    questions_last_n_days = [
        DailyCount(day=row[0].date(), count=row[1]) for row in daily_result.all()
    ]

    dept_result = await db.execute(
        select(ChatQuery.department, func.count(ChatQuery.id))
        .where(ChatQuery.department.is_not(None))
        .group_by(ChatQuery.department)
    )
    department_breakdown = [
        DepartmentCount(department=row[0], count=row[1]) for row in dept_result.all()
    ]

    agent_result = await db.execute(
        select(ChatQuery.agent_used, func.count(ChatQuery.id))
        .where(ChatQuery.agent_used.is_not(None))
        .group_by(ChatQuery.agent_used)
    )
    agent_usage = [
        DepartmentCount(department=row[0], count=row[1]) for row in agent_result.all()
    ]

    # Top searched topics: crude but dependency-free keyword frequency over
    # all questions, stopwords stripped. Good enough for a "what are people
    # asking about" signal without standing up a text-analytics pipeline.
    questions_result = await db.execute(select(ChatQuery.question))
    counter: Counter[str] = Counter()
    for (question,) in questions_result.all():
        tokens = [t for t in _TOKEN_RE.findall(question.lower()) if t not in _STOPWORDS and len(t) > 2]
        counter.update(tokens)
    top_topics = [TopicCount(keyword=k, count=c) for k, c in counter.most_common(10)]

    active_result = await db.execute(
        select(
            User.id, User.full_name, User.email, func.count(ChatQuery.id).label("cnt")
        )
        .join(ChatQuery, ChatQuery.user_id == User.id)
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(ChatQuery.id).desc())
        .limit(5)
    )
    most_active_users = [
        UserActivity(user_id=str(row[0]), full_name=row[1], email=row[2], question_count=row[3])
        for row in active_result.all()
    ]

    return AnalyticsSummary(
        total_questions=total_questions,
        failed_queries=failed_queries,
        failure_rate=failure_rate,
        questions_last_7_days=questions_last_n_days,
        department_breakdown=department_breakdown,
        agent_usage=agent_usage,
        top_topics=top_topics,
        most_active_users=most_active_users,
    )
