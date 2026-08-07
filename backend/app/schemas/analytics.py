from datetime import date

from pydantic import BaseModel


class DailyCount(BaseModel):
    day: date
    count: int


class TopicCount(BaseModel):
    keyword: str
    count: int


class DepartmentCount(BaseModel):
    department: str
    count: int


class UserActivity(BaseModel):
    user_id: str
    full_name: str
    email: str
    question_count: int


class AnalyticsSummary(BaseModel):
    total_questions: int
    failed_queries: int
    failure_rate: float
    questions_last_7_days: list[DailyCount]
    department_breakdown: list[DepartmentCount]
    agent_usage: list[DepartmentCount]
    top_topics: list[TopicCount]
    most_active_users: list[UserActivity]
