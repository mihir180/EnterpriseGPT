import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DocumentPermission(Base, UUIDPKMixin, TimestampMixin):
    """
    Explicit grant: this specific user may access this specific document,
    regardless of the document's `allowed_departments` and regardless of
    the user's own department. Used for exceptions — e.g. a single
    Technical employee who needs to see one HR document for an audit.
    """

    __tablename__ = "document_permissions"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_document_permission"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    document = relationship("Document", back_populates="permissions")
    user = relationship("User", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<DocumentPermission doc={self.document_id} user={self.user_id}>"
