import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class RetrievalMode(str, enum.Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"


class ChatQuery(Base, UUIDPKMixin, TimestampMixin):
    """
    A single question/answer exchange produced by the RAG pipeline.

    Phase 4 adds `department` + `agent_used` (which specialist agent
    answered, from multi-agent routing) and `retrieval_mode` (vector-only
    vs hybrid) — all purely for analytics/audit, not used in retrieval.
    """

    __tablename__ = "chat_queries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # List of citation dicts: [{document_id, chunk_id, filename, page_number, score}, ...]
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    context_used: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Phase 4: which department agent handled this (nullable — pre-Phase-4 rows have none)
    department: Mapped[str | None] = mapped_column(
        Enum("hr", "legal", "technical", "general", name="department", create_type=False),
        nullable=True,
    )
    agent_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retrieval_mode: Mapped[str] = mapped_column(
        String(20), default=RetrievalMode.HYBRID.value, nullable=False
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ChatQuery user={self.user_id} q={self.question[:30]!r}>"
