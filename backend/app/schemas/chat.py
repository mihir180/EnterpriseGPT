import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Department


class SourceCitation(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    filename: str
    page_number: int | None
    score: float


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Optional manual override — skip the router agent and force a department.
    department: Department | None = None
    # Optional manual override — restrict retrieval to specific documents,
    # still filtered through the caller's ACL.
    document_ids: list[uuid.UUID] | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceCitation]
    context_used: bool
    department: Department
    agent_used: str
    retrieval_mode: str


class ChatQueryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    answer: str
    sources: list[dict]
    context_used: bool
    department: Department | None
    agent_used: str | None
    retrieval_mode: str
    created_at: datetime
