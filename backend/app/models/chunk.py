import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DocumentChunk(Base, UUIDPKMixin, TimestampMixin):
    """
    Metadata record for a single text chunk of a document.

    The chunk's embedding vector itself lives in Qdrant, keyed by this row's
    `id` (used as the Qdrant point ID). Keeping chunk text + metadata in
    Postgres (source of truth) while vectors live in Qdrant (search index)
    keeps the two systems cleanly separated and lets us rebuild the vector
    index from Postgres if needed.
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Mirrors this row's `id` — stored explicitly for clarity/debugging when
    # cross-referencing Qdrant point payloads back to Postgres.
    embedding_status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)

    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
