import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"       # file saved, not yet processed
    PROCESSING = "processing"   # extraction/chunking/embedding in progress
    READY = "ready"             # searchable
    FAILED = "failed"           # processing error


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"


class Document(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Phase 4 ACL: list of department strings (e.g. ["hr"]). Empty list means
    # "visible to every authenticated user" (the Phase 1-3 default behavior).
    # Admins always see everything regardless of this field. See acl_service.
    allowed_departments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    uploader = relationship("User", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    permissions = relationship(
        "DocumentPermission", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document {self.filename} ({self.status})>"
